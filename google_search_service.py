import csv
import time
import urllib.parse
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """Raised when the search backend reports the daily/rate quota is exhausted.

    Signals the pipeline to checkpoint progress and stop, so a later run
    (e.g. the next day) can resume from where it left off.
    """


class SearchError(Exception):
    """Raised when a search page fails for a non-quota reason.

    Distinguishes a genuine failure (network/API error) from "no more results",
    so a failed query is retried rather than silently recorded as empty.
    """


# API error 'reason' tokens that indicate quota/rate exhaustion (seen on 403).
_QUOTA_REASONS = ("quota", "ratelimitexceeded", "dailylimitexceeded", "userratelimitexceeded")


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
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> SearchResults:
        """Perform a Google search and retrieve results.

        Handles pagination automatically to fetch up to max_results.

        Args:
            query: The search term or phrase.
            max_results: Maximum results to return (API limit: 100).
            sort_by_date: If True, sort results by date.
            region: Geographic region code for search results.
            date_from: Optional absolute start date (YYYY-MM-DD or YYYYMMDD).
            date_to: Optional absolute end date (YYYY-MM-DD or YYYYMMDD).

        Returns:
            List of search result dictionaries from the API.
            Empty list if no results or on error.
        """
        decoded_query = urllib.parse.unquote(query)
        logger.info("Searching for: %s", decoded_query)

        all_results: SearchResults = []
        max_results = min(max_results, self.MAX_RESULTS_PER_QUERY)

        for start_index in range(1, max_results + 1, self.RESULTS_PER_PAGE):
            try:
                results = self._fetch_page_with_retry(
                    decoded_query,
                    start_index,
                    max_results - len(all_results),
                    sort_by_date,
                    region,
                    date_from,
                    date_to,
                )
            except SearchError:
                # If we already gathered some results, keep them; otherwise let
                # the caller know this query failed (so it can be retried).
                if all_results:
                    logger.warning(
                        "Page error after partial results for '%s'; returning %d gathered.",
                        decoded_query, len(all_results),
                    )
                    break
                raise

            if results is None:
                break

            all_results.extend(results)

            for item in results:
                logger.debug("Found: %s", item.get("link", "N/A"))

            if len(all_results) >= max_results:
                break

        logger.info("Total results found: %d", len(all_results))
        return all_results

    def _fetch_page_with_retry(
        self,
        *args: Any,
        retries: int = 2,
        backoff: float = 2.0,
    ) -> SearchResults | None:
        """Call ``_fetch_page`` with retries on transient (non-quota) errors.

        QuotaExceededError propagates immediately (no point retrying). A
        SearchError is retried up to ``retries`` times with linear backoff
        before being re-raised.
        """
        for attempt in range(retries + 1):
            try:
                return self._fetch_page(*args)
            except SearchError:
                if attempt >= retries:
                    raise
                time.sleep(backoff * (attempt + 1))

    @staticmethod
    def _is_quota_error(error: HttpError) -> bool:
        """Return True only for genuine quota/rate-limit errors (429, or 403
        whose reason names a quota), not every 403 (e.g. invalid key)."""
        status = getattr(getattr(error, "resp", None), "status", None)
        if status == 429:
            return True
        if status == 403:
            return any(token in str(error).lower() for token in _QUOTA_REASONS)
        return False

    def _fetch_page(
        self,
        query: str,
        start_index: int,
        remaining: int,
        sort_by_date: bool,
        region: str,
        date_from: str | None,
        date_to: str | None,
    ) -> SearchResults | None:
        """Fetch a single page of search results.

        Args:
            query: The search query.
            start_index: Starting index for pagination.
            remaining: Number of results still needed.
            sort_by_date: Whether to sort by date.
            region: Geographic region code.
            date_from: Optional absolute start date (YYYY-MM-DD or YYYYMMDD).
            date_to: Optional absolute end date (YYYY-MM-DD or YYYYMMDD).

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

            sort_value = self._build_sort_param(sort_by_date, date_from, date_to)
            if sort_value:
                search_params["sort"] = sort_value

            result = self._service.cse().list(**search_params).execute()

            return result.get("items")

        except HttpError as e:
            if self._is_quota_error(e):
                logger.warning("Search quota exhausted at start_index %s.", start_index)
                raise QuotaExceededError(str(e)) from e
            logger.error("HTTP Error at start_index %s: %s", start_index, e)
            raise SearchError(str(e)) from e
        except Exception as e:
            logger.error("Error at start_index %s: %s", start_index, e)
            raise SearchError(str(e)) from e

    @staticmethod
    def _format_date(date_str: str | None) -> str | None:
        """Normalize a date string to YYYYMMDD or return None if invalid.

        Accepts "YYYY-MM-DD" or "YYYYMMDD". Returns None if parsing fails.
        """
        if not date_str:
            return None
        value = date_str.strip()
        if not value:
            return None
        try:
            if "-" in value:
                dt = datetime.strptime(value, "%Y-%m-%d")
                return dt.strftime("%Y%m%d")
            # Assume already compact format
            if len(value) == 8 and value.isdigit():
                # Basic validation by attempting parse
                dt = datetime.strptime(value, "%Y%m%d")
                return dt.strftime("%Y%m%d")
        except ValueError:
            pass
        logger.warning("invalid date format '%s'. Expected YYYY-MM-DD or YYYYMMDD. Ignoring.", date_str)
        return None

    def _build_sort_param(
        self,
        sort_by_date: bool,
        date_from: str | None,
        date_to: str | None,
    ) -> str | None:
        """Build the Google CSE 'sort' parameter based on options.

        - If a date range is provided, use 'date:r:YYYYMMDD:YYYYMMDD'.
        - Else if sort_by_date is True, use 'date'.
        - Otherwise, return None.
        """
        start = self._format_date(date_from)
        end = self._format_date(date_to)

        if start or end:
            # Default start to a very early date if only end provided
            if not start:
                start = "19700101"
            # Default end to today (UTC) if only start provided
            if not end:
                end = datetime.now(timezone.utc).strftime("%Y%m%d")
            return f"date:r:{start}:{end}"

        if sort_by_date:
            return "date"

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
            logger.info("Processing query: %s", query)
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

        logger.info("Saved %d links to %s", len(links), filepath)
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

        logger.info("Results saved to %s", filepath)

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
            logger.debug("No results found for %s", person)
            return

        for item in results:
            row_data = self._extract_csv_row(person, item)
            writer.writerow(row_data)

        logger.info("Added %d results for '%s'", len(results), person)

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
