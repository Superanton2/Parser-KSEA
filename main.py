from pathlib import Path

import pandas as pd

from configuration import (
    SEARCH_QUERY,
    API_KEY,
    SEARCH_ENGINE_ID,
    LINKS_TO_REMOVE,
    OUTPUT_CONFIG,
    SEARCH_CONFIG,
)
from data_sorting import DataSorting
from google_search_service import GoogleSearchService


def perform_search(
    search_queries: list[str],
    search_service: GoogleSearchService,
) -> dict[str, list[dict]]:
    """
    Perform Google searches for multiple queries.

    Args:
        search_queries: List of search terms/names to search for.
        search_service: Configured GoogleSearchService instance.

    Returns:
        Dictionary mapping queries to their search results.
    """
    print("Starting Google Custom Search API operations\n")
    return search_service.search_multiple_queries(
        search_queries,
        max_results=SEARCH_CONFIG.max_results,
        sort_by_date=SEARCH_CONFIG.sort_by_date,
        region=SEARCH_CONFIG.region,
        date_from=SEARCH_CONFIG.date_from,
        date_to=SEARCH_CONFIG.date_to,
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


def process_and_sort_data(input_csv: Path, output_csv: Path) -> None:
    """
    Process and sort the search results data.

    Args:
        input_csv: Path to input CSV with raw search results.
        output_csv: Path for sorted output CSV.
    """
    print("\nStarting Data Processing:")

    df = pd.read_csv(input_csv)
    sorter = DataSorting(df)

    print("Data preparation...")
    sorter.remove_duplicates().rename_person()
    sorter.remove_by_links(links=LINKS_TO_REMOVE)

    # Apply URL filtering
    sorter.apply_url_filter()

    # Fill missing data
    sorter.fill_all_blank_slots()

    sorter.apply_ai_filter()

    # Sort and save
    sorter.sort_by_column("Date", ascending=True)
    sorter.dataframe.to_csv(output_csv, index=False)

    print(f"Sorted data saved to {output_csv}")


def main(search_queries: list[str]) -> None:
    """
    Main function that orchestrates the search and sorting pipeline.

    Args:
        search_queries: List of people/terms to search for.
    """
    # Initialize the search service
    search_service = GoogleSearchService(API_KEY, SEARCH_ENGINE_ID)

    # Perform searches
    results_by_person = perform_search(search_queries, search_service)

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

    print("\nAll search operations completed successfully!")

    # Process and sort data
    sorted_csv = OUTPUT_CONFIG.sorted_results_path
    process_and_sort_data(raw_csv, sorted_csv)

    print("\nFinish")


if __name__ == "__main__":
    main(SEARCH_QUERY)
