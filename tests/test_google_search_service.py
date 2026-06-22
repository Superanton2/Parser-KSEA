"""Unit tests for quota/error classification (no network)."""

from types import SimpleNamespace

from google_search_service import GoogleSearchService


def _http_error(status, message=""):
    """Build an object shaped like googleapiclient's HttpError for the classifier."""
    class _E(Exception):
        def __init__(self):
            self.resp = SimpleNamespace(status=status)

        def __str__(self):
            return message

    return _E()


def test_429_is_quota():
    assert GoogleSearchService._is_quota_error(_http_error(429)) is True


def test_403_quota_only_when_reason_matches():
    assert GoogleSearchService._is_quota_error(
        _http_error(403, "Quota exceeded for quota metric 'Queries'")
    ) is True
    # A 403 for other reasons (e.g. bad key, API disabled) must NOT be quota.
    assert GoogleSearchService._is_quota_error(
        _http_error(403, "The request is missing a valid API key.")
    ) is False


def test_other_statuses_not_quota():
    assert GoogleSearchService._is_quota_error(_http_error(500)) is False
