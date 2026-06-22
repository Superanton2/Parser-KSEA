"""Offline smoke test: exercises the resumable search + sorting/filter logic
on real objects with fake Google services and a fake LLM (no network, no creds).

Run: .venv/bin/python smoke_test.py
"""

# This is a manual smoke-test script; skip it during pytest collection.
if __name__ != "__main__":
    import pytest

    pytest.skip(
        "smoke_test.py is a manual smoke-test script; skip during pytest collection",
        allow_module_level=True,
    )

import logging
import tempfile
from pathlib import Path

import pandas as pd

from configuration import SearchConfig
from data_sorting import DataSorting
from google_search_service import QuotaExceededError
from state_manager import StateManager
from main import perform_search

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("smoke")

QUERIES = ["Oleh Nivievskyi", "Maria Bogonos", "Pavlo Martyshev", "Roman Neyter"]


class FakeSearchService:
    """Returns one canned result per query; raises quota error after `limit` calls."""

    def __init__(self, quota_limit: int):
        self.quota_limit = quota_limit
        self.calls = 0

    def search(self, query, **kwargs):
        if self.calls >= self.quota_limit:
            raise QuotaExceededError("fake daily quota exhausted")
        self.calls += 1
        return [{
            "title": f"Article about {query}",
            "link": f"https://news.example.com/{query.replace(' ', '-').lower()}",
            "displayLink": "news.example.com",
            "pagemap": {"metatags": [{"article:published_time": "2024-05-01T10:00:00Z"}]},
        }]


class FakeLLM:
    """Classifies anything containing 'Article' as a real article."""
    def is_article(self, text: str) -> bool:
        return "Article" in text


def section(t): print(f"\n{'='*60}\n{t}\n{'='*60}")


def test_resume_on_quota(tmp: Path):
    section("1) Search hits quota after 2 queries -> checkpoint + resume")
    state_path = tmp / "state.json"
    cfg = SearchConfig(api_key="x", search_engine_id="y", max_results=10)

    # First run: quota allows only 2 of 4 queries
    svc1 = FakeSearchService(quota_limit=2)
    results, complete = perform_search(QUERIES, svc1, cfg, StateManager(state_path))
    log.info("run #1: complete=%s, queries collected=%d", complete, len(results))
    assert complete is False, "should be incomplete after quota"
    assert len(results) == 2, f"expected 2 done, got {len(results)}"
    assert state_path.exists(), "checkpoint must be saved"

    # Second run (next day): fresh quota, resumes the remaining 2
    svc2 = FakeSearchService(quota_limit=10)
    results2, complete2 = perform_search(QUERIES, svc2, cfg, StateManager(state_path))
    log.info("run #2: complete=%s, queries collected=%d, new API calls=%d",
             complete2, len(results2), svc2.calls)
    assert complete2 is True, "should complete on resume"
    assert len(results2) == 4, "all 4 queries present"
    assert svc2.calls == 2, "resume must only re-query the 2 unfinished ones"
    print("OK: resume skipped already-done queries and finished the rest.")
    return results2


def test_sort_and_filter(results: dict, tmp: Path):
    section("2) DataSorting pipeline (dedup + url filter + AI filter)")
    rows = []
    for person, items in results.items():
        for it in items:
            rows.append({"Person": person, "Title": it["title"], "Date": "2024-05-01",
                         "Source": it["displayLink"], "Link": it["link"]})
    # inject a duplicate, a blacklisted-domain row, and a non-article row
    rows.append(dict(rows[0]))  # duplicate link
    rows.append({"Person": "X", "Title": "spam", "Date": "", "Source": "bad.com",
                 "Link": "https://bad.com/x", "Title text": "Article spam"})
    rows.append({"Person": "Y", "Title": "dir", "Date": "", "Source": "ok.com",
                 "Link": "https://ok.com/listing", "Title text": "phone 123 contact"})
    df = pd.DataFrame(rows)
    df["Title text"] = df.get("Title text")
    df.loc[df["Title text"].isna(), "Title text"] = "Article body text here"

    sorter = DataSorting(
        df,
        blacklisted_domains=["bad.com"],
        url_stop_words=["listing"],
        rewrite_names={"Oleh Nivievskyi": "Oleh Nivievskyi (KSE)"},
        llm=FakeLLM(),
    )
    before = len(sorter.dataframe)
    sorter.remove_duplicates().rename_person()
    sorter.apply_url_filter()
    sorter.apply_ai_filter()
    after = len(sorter.dataframe)
    log.info("rows: %d -> %d after dedup/url/AI filters", before, after)
    persons = list(sorter.dataframe["Person"])
    print("Remaining persons:", persons)
    assert "https://bad.com/x" not in set(sorter.dataframe["Link"]), "blacklist domain not removed"
    assert "https://ok.com/listing" not in set(sorter.dataframe["Link"]), "stop word not removed"
    assert any("(KSE)" in p for p in persons), "rename not applied"
    print("OK: dedup, domain blacklist, URL stop-word, rename and AI filter all worked.")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        results = test_resume_on_quota(tmp)
        test_sort_and_filter(results, tmp)
    section("SMOKE TEST PASSED ✅")
