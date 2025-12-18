import csv
import urllib.parse
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Type aliases for clarity
SearchResult = dict[str, Any]
SearchResults = list[SearchResult]
QueryResults = dict[str, SearchResults]


class GoogleSearchService:
    """Service class for interacting with the Google Custom Search API.

    Encapsulates search logic, pagination handling, and result processing
    for CSV and text file exports.

    Attributes:
        _api_key: The Google Custom Search API key.
        _search_engine_id: The Custom Search Engine ID.
        _service: The Google API client service object.
    """

    # API limits
    MAX_RESULTS_PER_QUERY = 100
    RESULTS_PER_PAGE = 10

    # CSV column names
    CSV_COLUMNS = ["Person", "Title", "Date", "Source", "Link"]

    def __init__(self, api_key: str, search_engine_id: str) -> None:
        """Initialize the GoogleSearchService with API credentials.

        Args:
            api_key: Your Google Custom Search API key.
            search_engine_id: Your Custom Search Engine ID.
        """
        self._api_key = api_key
        self._search_engine_id = search_engine_id
        self._service = build("customsearch", "v1", developerKey=api_key)

    def search(
        self,
        query: str,
        max_results: int = 100,
        sort_by_date: bool = False,
        region: str = "ua",
    ) -> SearchResults:
        """Perform a Google search and retrieve results.

        Handles pagination automatically to fetch up to max_results.

        Args:
            query: The search term or phrase.
            max_results: Maximum results to return (API limit: 100).
            sort_by_date: If True, sort results by date.
            region: Geographic region code for search results.

        Returns:
            List of search result dictionaries from the API.
            Empty list if no results or on error.
        """
        decoded_query = urllib.parse.unquote(query)
        print(f"Searching for: {decoded_query}")

        all_results: SearchResults = []
        max_results = min(max_results, self.MAX_RESULTS_PER_QUERY)

        for start_index in range(1, max_results + 1, self.RESULTS_PER_PAGE):
            results = self._fetch_page(
                decoded_query,
                start_index,
                max_results - len(all_results),
                sort_by_date,
                region,
            )

            if results is None:
                break

            all_results.extend(results)

            for item in results:
                print(f"Found: {item.get('link', 'N/A')}")

            if len(all_results) >= max_results:
                break

        print(f"Total results found: {len(all_results)}")
        return all_results

    def _fetch_page(
        self,
        query: str,
        start_index: int,
        remaining: int,
        sort_by_date: bool,
        region: str,
    ) -> SearchResults | None:
        """Fetch a single page of search results.

        Args:
            query: The search query.
            start_index: Starting index for pagination.
            remaining: Number of results still needed.
            sort_by_date: Whether to sort by date.
            region: Geographic region code.

        Returns:
            List of results or None if no more results/error.
        """
        try:
            search_params = {
                "q": query,
                "cx": self._search_engine_id,
                "start": start_index,
                "gl": region,
                "num": min(self.RESULTS_PER_PAGE, remaining),
            }

            if sort_by_date:
                search_params["sort"] = "date"

            result = self._service.cse().list(**search_params).execute()

            return result.get("items")

        except HttpError as e:
            print(f"HTTP Error at start_index {start_index}: {e}")
        except Exception as e:
            print(f"Error at start_index {start_index}: {e}")

        return None

    def search_multiple_queries(
        self,
        queries: list[str],
        **search_params: Any,
    ) -> QueryResults:
        """Execute searches for multiple queries.

        Args:
            queries: List of search queries to execute.
            **search_params: Keyword arguments passed to search method
                (e.g., max_results, sort_by_date).

        Returns:
            Dictionary mapping queries to their search results.
        """
        results: QueryResults = {}

        for query in queries:
            print(f"\nProcessing query: {query}")
            results[query] = self.search(query, **search_params)

        return results

    def save_links_to_txt(
        self,
        results: SearchResults,
        filename: str | Path,
    ) -> int:
        """Save URLs from search results to a text file.

        Args:
            results: List of search result items.
            filename: Path to the output text file.

        Returns:
            Number of links saved.
        """
        links = self.get_links_only(results)
        filepath = Path(filename)

        filepath.write_text("\n".join(links) + "\n", encoding="utf-8")

        print(f"Saved {len(links)} links to {filepath}")
        return len(links)

    def save_to_csv(
        self,
        queries_results: QueryResults,
        filename: str | Path,
    ) -> None:
        """Save detailed search results to a CSV file.

        Args:
            queries_results: Dictionary mapping queries to their results.
            filename: Path to the output CSV file.
        """
        filepath = Path(filename)

        with filepath.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(self.CSV_COLUMNS)

            for person, results in queries_results.items():
                self._write_person_results(writer, person, results)

        print(f"\nResults saved to {filepath}")

    def _write_person_results(
        self,
        writer: Any,
        person: str,
        results: SearchResults,
    ) -> None:
        """Write results for a single person/query to CSV.

        Args:
            writer: CSV writer object.
            person: The person/query name.
            results: Search results for this person.
        """
        if not results:
            writer.writerow([person, "", "", "", ""])
            print(f"No results found for {person}")
            return

        for item in results:
            row_data = self._extract_csv_row(person, item)
            writer.writerow(row_data)

        print(f"Added {len(results)} results for '{person}'")

    def _extract_csv_row(self, person: str, item: SearchResult) -> list[str]:
        """Extract and format data for a CSV row.

        Args:
            person: The person/query associated with the result.
            item: A single search result from the API.

        Returns:
            Formatted list for CSV row: [person, title, date, source, link].
        """
        date = self._extract_date(item)

        return [
            person,
            item.get("title", ""),
            date or "",
            item.get("displayLink", ""),
            item.get("link", ""),
        ]

    @staticmethod
    def _extract_date(item: SearchResult) -> str | None:
        """Extract publication date from search result metadata.

        Args:
            item: A search result item.

        Returns:
            Date string if found, None otherwise.
        """
        pagemap = item.get("pagemap", {})
        metatags = pagemap.get("metatags", [])

        if metatags:
            return metatags[0].get("article:published_time")

        return None

    def get_links_only(self, results: SearchResults) -> list[str]:
        """Extract just the URLs from search results.

        Args:
            results: List of search result items.

        Returns:
            List of URL strings.
        """
        return [item.get("link", "") for item in results if "link" in item]
