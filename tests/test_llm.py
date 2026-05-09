import pytest

from llm import LLM


def test_heuristic_context_counts():
    l = LLM(model_name="m")
    ctx = l._heuristic_context("One paragraph.\n\nSecond paragraph.")
    assert "Words:" in ctx and "Paragraphs:" in ctx


def test_is_article_fallback_true(monkeypatch):
    l = LLM(model_name="m")

    # Force _create_completion to return empty so fallback heuristic is used
    monkeypatch.setattr(LLM, "_create_completion", lambda self, prompt, max_tokens=8, temperature=0.0: "")
    long_text = "word " * 300
    assert l.is_article(long_text) is True


def test_is_article_fallback_false(monkeypatch):
    l = LLM(model_name="m")
    monkeypatch.setattr(LLM, "_create_completion", lambda self, prompt, max_tokens=8, temperature=0.0: "")
    short_text = "short snippet"
    assert l.is_article(short_text) is False
