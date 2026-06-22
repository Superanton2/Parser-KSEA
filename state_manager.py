"""Resumable run state for the search pipeline.

The free Google Custom Search tier allows only ~100 queries/day, while a full
run issues several hundred API calls. When the quota is hit mid-run we cannot
finish in one pass, so progress is checkpointed to a JSON file: which queries
already completed and the results they returned. A later run (typically the
next day, triggered by the systemd timer) loads the checkpoint and continues
with the remaining queries only. Once every query is done the state is cleared.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SearchResults = list[dict[str, Any]]


class StateManager:
    """Persist and restore per-query search progress across runs."""

    def __init__(self, path: str | Path = "search_state.json") -> None:
        self.path = Path(path)
        # query -> list of result items already fetched for that query
        self._completed: dict[str, SearchResults] = {}
        # query -> number of failed (non-quota) attempts so far
        self._failures: dict[str, int] = {}
        self.load()

    def load(self) -> None:
        """Load checkpoint from disk if it exists; start fresh otherwise."""
        if not self.path.exists():
            self._completed = {}
            self._failures = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            raw = raw if isinstance(raw, dict) else {}
            completed = raw.get("completed", {})
            failures = raw.get("failures", {})
            self._completed = completed if isinstance(completed, dict) else {}
            self._failures = failures if isinstance(failures, dict) else {}
            logger.info("Loaded search state: %d queries already done.", len(self._completed))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Could not read state file %s: %s. Starting fresh.", self.path, e)
            self._completed = {}
            self._failures = {}

    def _save(self) -> None:
        """Atomically write the checkpoint to disk."""
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.write_text(
                json.dumps(
                    {"completed": self._completed, "failures": self._failures},
                    ensure_ascii=False, indent=2,
                ),
                encoding="utf-8",
            )
            tmp.replace(self.path)
        except OSError as e:
            logger.error("Failed to write state file %s: %s", self.path, e)

    def is_done(self, query: str) -> bool:
        """Return True if this query was already completed in an earlier run."""
        return query in self._completed

    def mark_done(self, query: str, results: SearchResults) -> None:
        """Record a query's results and persist the checkpoint immediately."""
        self._completed[query] = results
        self._failures.pop(query, None)
        self._save()

    def record_failure(self, query: str) -> int:
        """Increment and persist the failed-attempt count for a query.

        Returns the new cumulative failure count.
        """
        self._failures[query] = self._failures.get(query, 0) + 1
        self._save()
        return self._failures[query]

    def get_results(self, query: str) -> SearchResults:
        """Return stored results for a completed query (empty list if none)."""
        return self._completed.get(query, [])

    def all_results(self) -> dict[str, SearchResults]:
        """Return the full query -> results mapping accumulated so far."""
        return dict(self._completed)

    def clear(self) -> None:
        """Drop all state and delete the checkpoint file (run fully finished)."""
        self._completed = {}
        self._failures = {}
        try:
            self.path.unlink(missing_ok=True)
        except OSError as e:
            logger.error("Failed to remove state file %s: %s", self.path, e)
