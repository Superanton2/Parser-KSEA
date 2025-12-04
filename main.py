import pandas as pd

from configuration import SEARCH_QUERY, API_KEY, SEARCH_ENGINE_ID, links_to_remove
from data_sorting import DataSorting
from google_search_service import GoogleSearchService


def main(search_query: list[str]):
    """
    the main function that combines all three blocks of code together

    :param search_query: enter list of people who will be searched
    :return: nothing
    """

    # # Initialize the service
    # search_service = GoogleSearchService(API_KEY, SEARCH_ENGINE_ID)
    #
    # # Perform searches for multiple people
    # print("Starting Google Custom Search API operations\n")
    # results_by_person = search_service.search_multiple_queries(
    #     search_query,
    #     max_results=100,
    #     sort_by_date=True
    # )
    #
    # # Save results to CSV
    # search_service.save_to_csv(results_by_person, "google_search_results.csv")
    #
    # # Optionally save links to TXT for a specific query
    # if search_query:
    #     first_query_results = results_by_person.get(SEARCH_QUERY[0], [])
    #     search_service.save_links_to_txt(first_query_results, "google_links.txt")
    #
    # print("\nAll operations completed successfully!")

    """Sorting"""
    print("\nStarting Data Processing:")

    ds = DataSorting(pd.read_csv("google_search_results.csv"))


    print("Data preparation...")
    # ds.remove_duplicates().rename_person()

    # filtering with filters
    # ds.apply_url_filter()

    ds.fill_all_blank_slots()

    # ds.apply_ai_filtering()
    # ds.remove_by_links(links=links_to_remove)

    print("Search by dates...")
    # ds.clean_dates()
    # ds.sort_by_column("Date", ascending=True)
    ds.dataframe.to_csv("google_links_sorted.csv", index=False)
    """Sorting"""
    print("Finish")


if __name__ == "__main__":
    main(SEARCH_QUERY)
