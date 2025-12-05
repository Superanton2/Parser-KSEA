import csv
import urllib.parse
from datetime import datetime
from typing import List, Dict

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSearchService:
    """
    A service class to interact with the Google Custom Search API.

    This class encapsulates the logic for performing searches, handling pagination,
    and processing the results into various formats like CSV or a simple list of links.
    It is designed to be reusable and easy to configure with an API key and a
    Custom Search Engine ID.

    Attributes:
        _api_key (str): The Google Custom Search API key.
        _search_engine_id (str): The ID of the Custom Search Engine to use.
        _service: The Google API client service object.
    """

    def __init__(self, api_key: str, search_engine_id: str):
        """Initializes the GoogleSearchService with API credentials.

        Args:
            api_key (str): Your Google Custom Search API key.
            search_engine_id (str): Your Custom Search Engine ID.
        """
        self._api_key = api_key
        self._search_engine_id = search_engine_id
        self._service = build("customsearch", "v1", developerKey=api_key)

    def search(self, query: str, max_results: int = 100, sort_by_date: bool = False) -> List[Dict]:
        """Performs a Google search and retrieves a list of results.

        This method queries the Google Custom Search API. It handles pagination by making
        multiple requests if necessary to fetch up to `max_results`. The number of
        results is capped at 100, which is a limitation of the API.

        Args:
            query (str): The search term or phrase.
            max_results (int, optional): The maximum number of search results to return.
                Defaults to 100. The API limit is 100.
            sort_by_date (bool, optional): If True, results will be sorted by date.
                Defaults to False.

        Returns:
            List[Dict]: A list of dictionary objects, where each dictionary represents
                        a single search result item from the API. Returns an empty
                        list if no results are found or an error occurs.
        """
        decoded_query = urllib.parse.unquote(query)
        print(f"Searching for: {decoded_query}")

        all_results = []
        max_results = min(max_results, 100)

        for start_index in range(1, max_results + 1, 10):
            try:
                search_params = {
                    'q': decoded_query,
                    'cx': self._search_engine_id,
                    'start': start_index,
                    'gl': 'ua',

                    'num': min(10, max_results - len(all_results))
                }

                if sort_by_date:
                    search_params['sort'] = 'date'

                result = self._service.cse().list(**search_params).execute()

                if 'items' in result:
                    all_results.extend(result['items'])
                    for item in result['items']:
                        print(f"Found: {item.get('link', 'N/A')}")
                else:
                    break

                if len(all_results) >= max_results:
                    break

            except HttpError as e:
                print(f"HTTP Error at start_index {start_index}: {e}")
                break
            except Exception as e:
                print(f"Error at start_index {start_index}: {e}")
                break

        print(f"Total results found: {len(all_results)}")
        return all_results

    def search_multiple_queries(self, queries: List[str], **search_params) -> Dict[str, List[Dict]]:
        """Executes a search for each query in a given list.

        This method iterates through a list of queries, performs a search for each one
        using the `search` method, and aggregates the results into a dictionary.

        Args:
            queries (List[str]): A list of search queries to execute.
            **search_params: Keyword arguments to be passed to the `search` method,
                             such as `max_results` or `sort_by_date`.

        Returns:
            Dict[str, List[Dict]]: A dictionary where keys are the original queries
                                   and values are the corresponding lists of search
                                   results.
        """
        results = {}
        for query in queries:
            print(f"\nProcessing query: {query}")
            results[query] = self.search(query, **search_params)
        return results

    def save_links_to_txt(self, results: List[Dict], filename: str) -> int:
        """Saves the URLs from search results to a text file.

        Each URL is written on a new line.

        Args:
            results (List[Dict]): A list of search result items.
            filename (str): The path to the output text file.

        Returns:
            int: The number of links that were successfully saved to the file.
        """
        links = [item.get('link', '') for item in results if 'link' in item]

        with open(filename, "w", encoding="utf-8") as file:
            for link in links:
                file.write(link + "\n")

        print(f"Saved {len(links)} links to {filename}")
        return len(links)

    def save_to_csv(self, queries_results: Dict[str, List[Dict]], filename: str) -> None:
        """Saves detailed search results to a CSV file.

        The CSV file will have the columns: 'Person', 'Title', 'Date', 'Source', 'Link'.
        For each query, its results are appended to the file. If a query has no
        results, a single row with the person's name is added.

        Args:
            queries_results (Dict[str, List[Dict]]): A dictionary mapping a query (person)
                to their list of search results.
            filename (str): The path to the output CSV file.
        """
        # Create file with header
        with open(filename, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(['Person', 'Title', 'Date', 'Source', 'Link'])

        # Append results for each query
        with open(filename, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            for person, results in queries_results.items():
                if not results:
                    # Write empty row if no results
                    writer.writerow([person, '', '', '', ''])
                    print(f"No results found for {person}")
                else:
                    for item in results:
                        row_data = self._extract_csv_row(person, item)
                        writer.writerow(row_data)
                    print(f"Added {len(results)} results for '{person}'")

        print(f"\nResults saved to {filename}")

    def _extract_csv_row(self, person: str, item: Dict) -> List[str]:
        """Extracts and formats data for a single CSV row from a search result item.

        This helper method attempts to find a publication date from the result's
        metadata.

        Args:
            person (str): The name of the person or query associated with the result.
            item (Dict): A single search result item from the Google Search API.

        Returns:
            List[str]: A list of strings formatted for a CSV row:
                       [person, title, date, source, link].
        """
        # Try to extract date from metadata
        date = ''
        if 'pagemap' in item and 'metatags' in item['pagemap']:
            metatags = item['pagemap']['metatags']
            if metatags and len(metatags) > 0:
                date = metatags[0].get('article:published_time', '')

        if not date:
            # date = datetime.now().strftime('%Y-%m-%d')
            date = None

        return [
            person,
            item.get('title', ''),
            date,
            item.get('displayLink', ''),
            item.get('link', '')
        ]

    def get_links_only(self, results: List[Dict]) -> List[str]:
        """Extracts just the URLs from a list of search results.

        Args:
            results (List[Dict]): A list of search result items.

        Returns:
            List[str]: A list containing only the URL strings from the results.
        """
        return [item.get('link', '') for item in results if 'link' in item]
