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
from google_search_service import GoogleSearchService
from google_sheets_manager import GoogleSheetsManager, GoogleSheetsLogHandler

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

    search_config = SearchConfig(
        api_key=bot_params.get("API_KEY", ""),
        search_engine_id=bot_params.get("SEARCH_ENGINE_ID", ""),
        max_results=int(bot_params.get("MAX_RESULTS", 100)),
        date_from=bot_params.get("DATE_FROM", None),
        date_to=bot_params.get("DATE_TO", None)
    )

    return gs_manager, search_config, search_queries, blacklists, bot_params

def perform_search(
    search_queries: list[str],
    search_service: GoogleSearchService,
    search_config: SearchConfig
) -> dict[str, list[dict]]:
    """
    Perform Google searches for multiple queries.

    Args:
        search_queries: List of search terms/names to search for.
        search_service: Configured GoogleSearchService instance.
        search_config: Configuration for Search

    Returns:
        Dictionary mapping queries to their search results.
    """
    logging.getLogger(__name__).info("Starting Google Custom Search API operations")
    return search_service.search_multiple_queries(
        search_queries,
        max_results=search_config.max_results,
        sort_by_date=search_config.sort_by_date,
        region=search_config.region,
        date_from=search_config.date_from,
        date_to=search_config.date_to,
    )


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
        gs_manager: GoogleSheetsManager
) -> None:
    """
    Process and sort the search results data.

    Args:
        input_csv: Path to input CSV with raw search results.
        output_csv: Path for sorted output CSV.
        blacklists: Dictionary of link to remove
        gs_manager:
    """
    logging.getLogger(__name__).info("Starting Data Processing")

    df = pd.read_csv(input_csv)
    sorter = DataSorting(df)
    sorter = DataSorting(
        df,
        blacklisted_domains=blacklists["domains"],
        url_stop_words=blacklists["stop_words"]
    )

    logging.getLogger(__name__).info("Data preparation...")
    sorter.remove_duplicates().rename_person()
    sorter.remove_by_links(links=blacklists["links_to_remove"])

    # Apply URL filtering
    sorter.apply_url_filter()

    # Fill missing data
    sorter.fill_all_blank_slots()

    sorter.apply_ai_filter()

    # Sort and save
    sorter.sort_by_column("Date", ascending=True)
    sorter.dataframe.to_csv(output_csv, index=False)

    logging.getLogger(__name__).info("Sorted data saved to %s", output_csv)

    gs_manager.append_results(sorter.dataframe)
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
    CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "KSE_Agrocenter_Parser")

    gs_manager, search_config, search_queries, blacklists, bot_params = init_environment(
        CREDENTIALS_PATH, SPREADSHEET_NAME
    )

    # Initialize the search service
    search_service = GoogleSearchService(search_config.api_key, search_config.search_engine_id)

    # Perform searches
    results_by_person = perform_search(search_queries, search_service, search_config)

    # Save raw results
    raw_csv = OUTPUT_CONFIG.search_results_path
    links_txt = OUTPUT_CONFIG.links_path
    save_search_results(
        results_by_person,
        search_service,
        search_queries,
        raw_csv,
        links_txt,
    )

    logging.getLogger(__name__).info("All search operations completed successfully!")

    # Process and sort data
    sorted_csv = OUTPUT_CONFIG.sorted_results_path
    process_and_sort_data(raw_csv, sorted_csv, blacklists, gs_manager)
    save_to_Google_Drive(bot_params, gs_manager, raw_csv, sorted_csv)

    logging.getLogger(__name__).info("Finish")
    logging.shutdown()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()