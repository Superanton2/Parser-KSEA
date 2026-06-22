from pathlib import Path
import pandas as pd
import logging

import os
from dotenv import load_dotenv
load_dotenv()

from configuration import (
    SearchConfig,
    OUTPUT_CONFIG,
)
from data_sorting import DataSorting
from google_search_service import GoogleSearchService, QuotaExceededError
from searxng_service import SearxngSearchService
from google_sheets_manager import GoogleSheetsManager, GoogleSheetsLogHandler
from llm import LLM
from state_manager import StateManager


def build_search_service(bot_params: dict, search_config: SearchConfig):
    """Pick the search backend based on config (SEARCH_PROVIDER key/env).

    'searxng' uses a self-hosted SearXNG instance (SEARXNG_URL); anything else
    (default) uses the Google Custom Search API.
    """
    provider = str(
        bot_params.get("SEARCH_PROVIDER") or os.getenv("SEARCH_PROVIDER", "google")
    ).strip().lower()

    if provider == "searxng":
        base_url = bot_params.get("SEARXNG_URL") or os.getenv("SEARXNG_URL", "http://localhost:8888")
        logging.getLogger(__name__).info("Using SearXNG search backend at %s", base_url)
        return SearxngSearchService(base_url=base_url)

    logging.getLogger(__name__).info("Using Google Custom Search backend")
    return GoogleSearchService(search_config.api_key, search_config.search_engine_id)

def init_environment(credentials_path: str, spreadsheet_name: str) -> tuple:
    """
    Initialize all services and get config data
    Args:
        credentials_path:
        spreadsheet_name:
    Returns:
        Tuple with gs_manager, search_config, search_queries, blacklists
    """
    logger = logging.getLogger(__name__)
    logger.info("Initialize all services and get config data")

    gs_manager = GoogleSheetsManager(credentials_path, spreadsheet_name)
    bot_params = gs_manager.get_bot_params()

    batch_size = int(bot_params.get("LOG_BATCH_SIZE", 25))
    gs_handler = GoogleSheetsLogHandler(gs_manager, batch_size=batch_size)
    gs_handler.setLevel(logging.INFO)

    gs_formatter = logging.Formatter('%(message)s')
    gs_handler.setFormatter(gs_formatter)

    logging.getLogger().addHandler(gs_handler)

    logger = logging.getLogger(__name__)
    logger.info("Initialize all services and get config data")

    search_queries = gs_manager.get_search_queries()
    blacklists = gs_manager.get_blacklists()

    # MAX_RESULTS env var overrides the sheet value (useful for bounding runs
    # against the daily quota or for quick tests).
    max_results = int(os.getenv("MAX_RESULTS") or bot_params.get("MAX_RESULTS", 100))

    search_config = SearchConfig(
        api_key=bot_params.get("API_KEY", ""),
        search_engine_id=bot_params.get("SEARCH_ENGINE_ID", ""),
        max_results=max_results,
        date_from=bot_params.get("DATE_FROM", None),
        date_to=bot_params.get("DATE_TO", None)
    )

    return gs_manager, search_config, search_queries, blacklists, bot_params

def perform_search(
    search_queries: list[str],
    search_service: GoogleSearchService,
    search_config: SearchConfig,
    state: StateManager,
) -> tuple[dict[str, list[dict]], bool]:
    """
    Perform Google searches for multiple queries, resuming from saved state.

    Queries already completed in an earlier run are skipped (their cached
    results are reused). If the search quota is exhausted mid-run, progress is
    checkpointed and the function returns early with ``complete=False`` so a
    later run can finish the remaining queries.

    Args:
        search_queries: List of search terms/names to search for.
        search_service: Configured GoogleSearchService instance.
        search_config: Configuration for Search.
        state: StateManager holding per-query checkpoint data.

    Returns:
        Tuple of (results mapping query -> results, complete flag).
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting Google Custom Search API operations")

    results_by_person: dict[str, list[dict]] = state.all_results()
    complete = True

    for query in search_queries:
        if state.is_done(query):
            logger.debug("Skipping already-completed query: %s", query)
            continue
        try:
            results = search_service.search(
                query,
                max_results=search_config.max_results,
                sort_by_date=search_config.sort_by_date,
                region=search_config.region,
                date_from=search_config.date_from,
                date_to=search_config.date_to,
            )
        except QuotaExceededError:
            logger.warning(
                "Search quota exhausted on query '%s'. Checkpointing; "
                "remaining queries will run on the next scheduled execution.",
                query,
            )
            complete = False
            break

        state.mark_done(query, results)
        results_by_person[query] = results

    return results_by_person, complete


def save_search_results(
    results_by_person: dict[str, list[dict]],
    search_service: GoogleSearchService,
    search_queries: list[str],
    output_csv: Path,
    output_txt: Path
) -> None:
    """
    Save search results to CSV and TXT files.

    Args:
        results_by_person: Dictionary of search results by query.
        search_service: GoogleSearchService instance for saving.
        search_queries: Original list of queries.
        output_csv: Path for CSV output.
        output_txt: Path for TXT output with links.
    """
    search_service.save_to_csv(results_by_person, str(output_csv))

    if search_queries:
        first_query_results = results_by_person.get(search_queries[0], [])
        search_service.save_links_to_txt(first_query_results, str(output_txt))


def process_and_sort_data(
        input_csv: Path,
        output_csv: Path,
        blacklists: dict,
        gs_manager: GoogleSheetsManager,
        llm: LLM | None = None,
) -> None:
    """
    Process and sort the search results data.

    Args:
        input_csv: Path to input CSV with raw search results.
        output_csv: Path for sorted output CSV.
        blacklists: Dict with 'domains', 'stop_words', 'links_to_remove',
            and 'rewrite_names'.
        gs_manager: Sheets manager used to append the final results.
        llm: Optional LLM instance for the relevance filter.
    """
    logging.getLogger(__name__).info("Starting Data Processing")

    df = pd.read_csv(input_csv)
    sorter = DataSorting(
        df,
        blacklisted_domains=blacklists["domains"],
        url_stop_words=blacklists["stop_words"],
        rewrite_names=blacklists.get("rewrite_names", {}),
        llm=llm,
    )

    logging.getLogger(__name__).info("Data preparation...")
    sorter.remove_duplicates().rename_person()
    sorter.remove_by_links(links=blacklists["links_to_remove"])

    # Apply URL filtering
    sorter.apply_url_filter()

    # Fill missing data
    sorter.fill_all_blank_slots()

    # Score relevance 0-5 instead of dropping rows; humans triage in the sheet.
    sorter.add_relevance_scores()

    # Most relevant first, then newest.
    sorter.sort_by_multiple_columns(["Relevance", "Date"], ascending=[False, False])

    # Surface the score and key fields up front for easy review/transfer.
    df = sorter.dataframe
    lead = [c for c in ["Relevance", "Person", "Title", "Date", "Source", "Link"] if c in df.columns]
    df = df[lead + [c for c in df.columns if c not in lead]]

    df.to_csv(output_csv, index=False)
    logging.getLogger(__name__).info("Sorted data saved to %s", output_csv)

    gs_manager.append_results(df)
    logging.getLogger(__name__).info("Sorted data saved to Google Sheets.")


def save_to_Google_Drive(bot_params, gs_manager, raw_csv, sorted_csv):
    # Save to Google Drive
    drive_folder_id = bot_params.get("drive_folder_id")
    if not drive_folder_id:
        logging.getLogger(__name__).warning("No 'drive_folder_id' found in Bot_Params. Skipping Drive upload.")
        return

    logging.getLogger(__name__).info("Uploading CSV results to Google Drive...")

    raw_link = gs_manager.upload_file_to_drive(str(raw_csv), drive_folder_id)
    sorted_link = gs_manager.upload_file_to_drive(str(sorted_csv), drive_folder_id)

    gs_manager.save_links_to_dashboard(raw_link, sorted_link)


def main() -> None:
    """
    Main function that orchestrates the search and sorting pipeline.
    """
    logger = logging.getLogger(__name__)

    CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "KSE_Agrocenter_Parser")
    STATE_PATH = os.getenv("SEARCH_STATE_PATH", "search_state.json")

    gs_manager, search_config, search_queries, blacklists, bot_params = init_environment(
        CREDENTIALS_PATH, SPREADSHEET_NAME
    )

    # Initialize the search service (Google CSE or SearXNG) and resumable state
    search_service = build_search_service(bot_params, search_config)
    state = StateManager(STATE_PATH)

    # Perform searches (resumes from checkpoint; may stop early on quota)
    results_by_person, complete = perform_search(
        search_queries, search_service, search_config, state
    )

    # Save raw results (whatever we have so far) so links can be reviewed
    raw_csv = OUTPUT_CONFIG.search_results_path
    links_txt = OUTPUT_CONFIG.links_path
    save_search_results(
        results_by_person,
        search_service,
        search_queries,
        raw_csv,
        links_txt,
    )

    if not complete:
        logger.warning(
            "Run incomplete: search quota was exhausted. Raw results saved to %s. "
            "The next scheduled run will resume the remaining queries.",
            raw_csv,
        )
        logging.shutdown()
        return

    logger.info("All search operations completed successfully!")

    # Build the LLM used by the relevance filter. Model/backend come from
    # Bot_Params, with env overrides (LLM_MODEL, USE_OLLAMA) for ops tuning.
    llm_model = os.getenv("LLM_MODEL") or bot_params.get("LLM_MODEL", "llama3.1:8b")
    use_ollama = str(
        os.getenv("USE_OLLAMA") or bot_params.get("USE_OLLAMA", "true")
    ).strip().lower() in ("1", "true", "yes")
    llm = LLM(model_name=llm_model, use_ollama=use_ollama)

    # Process and sort data
    sorted_csv = OUTPUT_CONFIG.sorted_results_path
    process_and_sort_data(raw_csv, sorted_csv, blacklists, gs_manager, llm=llm)
    save_to_Google_Drive(bot_params, gs_manager, raw_csv, sorted_csv)

    # Full run finished — clear checkpoint so the next run starts fresh
    state.clear()

    logger.info("Finish")
    logging.shutdown()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()