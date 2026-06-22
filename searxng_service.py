"""SearXNG-backed search service.

A drop-in replacement for :class:`GoogleSearchService` that queries a
self-hosted `SearXNG <https://docs.searxng.org/>`_ instance via its JSON API
instead of the Google Custom Search API (which is being retired and is
quota-limited). Results are normalised into the same dict shape Google returns,
so the rest of the pipeline (CSV export, sorting, filtering) is unchanged.

The SearXNG instance must have the ``json`` output format enabled in its
``settings.yml`` (``search.formats: [html, json]``).
"""

import time
import urllib.parse
from typing import Any

import requests

from google_search_service import GoogleSearchService, QuotaExceededError, SearchError, logger


class SearxngSearchService(GoogleSearchService):
    """Search via a SearXNG JSON endpoint, shaped like the Google CSE service."""

    def __init__(self, base_url: str = "http://localhost:8888", timeout: int = 20) -> None:
        # Intentionally do NOT call super().__init__: we have no Google client.
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._api_key = ""
        self._search_engine_id = ""

    def search(
        self,
        query: str,
        max_results: int = 100,
        sort_by_date: bool = False,
        region: str = "ua",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query SearXNG, paginating until ``max_results`` are gathered.

        ``date_from`` / ``date_to`` (absolute ranges) are not supported by
        SearXNG and are ignored here; dates are recovered later during
        enrichment. The signature matches GoogleSearchService for drop-in use.
        """
        decoded_query = urllib.parse.unquote(query)
        logger.info("Searching (SearXNG) for: %s", decoded_query)
        if date_from or date_to:
            logger.debug("SearXNG ignores absolute date ranges; recovered during enrichment.")

        all_results: list[dict[str, Any]] = []
        seen: set[str] = set()

        for page in range(1, 11):  # SearXNG paginates; cap to avoid runaway loops
            try:
                items = self._fetch_searx_page(decoded_query, page, region)
            except SearchError:
                if all_results:
                    logger.warning(
                        "SearXNG page error after partial results for '%s'; returning %d.",
                        decoded_query, len(all_results),
                    )
                    break
                raise
            if not items:
                break

            for r in items:
                url = r.get("url", "")
                if not url or url in seen:
                    continue
                seen.add(url)
                all_results.append(self._to_google_shape(r))
                if len(all_results) >= max_results:
                    break

            if len(all_results) >= max_results:
                break

        logger.info("Total results found (SearXNG): %d", len(all_results))
        return all_results[:max_results]

    def _fetch_searx_page(self, query: str, page: int, region: str) -> list[dict[str, Any]] | None:
        """Fetch one page of SearXNG JSON results."""
        params = {
            "q": query,
            "format": "json",
            "pageno": page,
            "categories": "general",
            "safesearch": 0,
        }
        try:
            resp = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=self._timeout,
                headers={"User-Agent": "ksea-parser/1.0"},
            )
        except requests.RequestException as e:
            logger.error("SearXNG request failed (page %s): %s", page, e)
            raise SearchError(str(e)) from e

        if resp.status_code == 429:
            # Mirror the CSE quota signal so the StateManager can checkpoint.
            logger.warning("SearXNG rate-limited (HTTP 429) on page %s.", page)
            raise QuotaExceededError("SearXNG returned HTTP 429")
        if resp.status_code != 200:
            logger.error("SearXNG returned HTTP %s on page %s.", resp.status_code, page)
            raise SearchError(f"SearXNG HTTP {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as e:
            logger.error("SearXNG response was not JSON — is the 'json' format enabled in settings.yml?")
            raise SearchError("SearXNG response was not JSON") from e

        # Be polite to the instance between pages.
        time.sleep(0.5)
        return data.get("results", [])

    @staticmethod
    def _to_google_shape(r: dict[str, Any]) -> dict[str, Any]:
        """Normalise a SearXNG result into the Google CSE item shape."""
        url = r.get("url", "")
        item: dict[str, Any] = {
            "title": r.get("title", ""),
            "link": url,
            "displayLink": urllib.parse.urlparse(url).netloc,
        }
        published = r.get("publishedDate")
        if published:
            item["pagemap"] = {"metatags": [{"article:published_time": published}]}
        return item
