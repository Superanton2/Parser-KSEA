import pandas as pd
import pytest

from data_sorting import DataSorting


class FakeLLM:
    def __init__(self, answers):
        self.answers = answers

    def is_article(self, text: str) -> bool:
        # Return based on substring presence for deterministic tests
        for key, val in self.answers.items():
            if key in text:
                return val
        return True

    def score_relevance(self, person: str, title: str, text: str) -> int:
        # Deterministic: score by substring presence in the text
        for key, val in self.answers.items():
            if key in (text or ""):
                return val
        return 3


def make_df(rows):
    return pd.DataFrame(rows)


def test_sort_by_column_success():
    df = make_df([
        {"Link": "a", "Person": "x", "Date": "2022-01-02", "Title text": "t1"},
        {"Link": "b", "Person": "y", "Date": "2021-01-01", "Title text": "t2"},
    ])
    sorter = DataSorting(df.copy())
    sorted_df = sorter.sort_by_column("Date", ascending=True, inplace=False)
    assert list(sorted_df["Link"]) == ["b", "a"]


def test_sort_by_column_missing():
    df = make_df([{"Link": "a", "Person": "x"}])
    sorter = DataSorting(df)
    with pytest.raises(ValueError):
        sorter.sort_by_column("Date")


def test_remove_by_links():
    df = make_df([
        {"Link": "https://good.com/page", "Person": "x"},
        {"Link": "https://bad.com/page", "Person": "y"},
    ])
    sorter = DataSorting(df.copy())
    sorter.remove_by_links(["bad.com"])
    assert "bad.com" not in " ".join(sorter.dataframe["Link"].tolist())


def test_remove_duplicates():
    df = make_df([
        {"Link": "https://a.com", "Person": "x"},
        {"Link": "https://a.com", "Person": "x"},
    ])
    sorter = DataSorting(df)
    sorter.remove_duplicates()
    assert len(sorter.dataframe) == 1


def test_rename_person():
    df = make_df([
        {"Link": "l", "Person": "Oleg Nivievskyi"},
    ])
    sorter = DataSorting(df, rewrite_names={"Oleg Nivievskyi": "Oleh Nivievskyi"})
    sorter.rename_person()
    assert "Oleh Nivievskyi" in sorter.dataframe["Person"].iloc[0]


def test_apply_url_filter_and_domain_blacklist():
    df = make_df([
        {"Link": "https://good.com/page", "Person": "x"},
        {"Link": "https://bad.com/page", "Person": "y"},
        {"Link": "https://site.com/stopword/page", "Person": "z"},
    ])
    sorter = DataSorting(df, blacklisted_domains=["bad.com"], url_stop_words=["stopword"])
    sorter.apply_url_filter()
    links = sorter.dataframe["Link"].tolist()
    assert all("bad.com" not in l for l in links)
    assert all("stopword" not in l for l in links)


def test_fill_all_blank_slots_calls_fill(monkeypatch):
    df = make_df([
        {"Link": "https://a.com", "Person": "x"},
        {"Link": "https://b.com", "Person": "y"},
    ])
    sorter = DataSorting(df)
    calls = []

    def fake_fill(idx):
        calls.append(idx)
        return True

    monkeypatch.setattr(sorter, "_fill_single_blank_slot", fake_fill)
    sorter.fill_all_blank_slots()
    assert calls == [0, 1]


def test_apply_ai_filter_with_injected_llm():
    df = make_df([
        {"Link": "l1", "Person": "p", "Title text": "this contains NO_ARTICLE"},
        {"Link": "l2", "Person": "p", "Title text": "this looks like an article"},
    ])
    fake = FakeLLM({"NO_ARTICLE": False})
    sorter = DataSorting(df, llm=fake)
    sorter.apply_ai_filter()
    assert len(sorter.dataframe) == 1


def test_add_relevance_scores_keeps_all_rows():
    df = make_df([
        {"Link": "l1", "Person": "p", "Title": "t1", "Title text": "irrelevant SPAM here"},
        {"Link": "l2", "Person": "p", "Title": "t2", "Title text": "a real article body"},
    ])
    fake = FakeLLM({"SPAM": 0, "real article": 5})
    sorter = DataSorting(df, llm=fake)
    sorter.add_relevance_scores()
    # No rows dropped, and a Relevance column with the expected scores exists.
    assert len(sorter.dataframe) == 2
    assert list(sorter.dataframe["Relevance"]) == [0, 5]


def test_check_relevance_and_is_domain_blacklisted():
    df = make_df([{"Link": "not-a-string", "Person": "p"}])
    sorter = DataSorting(df, blacklisted_domains=["example.com"])
    # Non-string => False
    assert sorter._check_relevance(123) is False
    # Domain matching
    assert sorter._is_domain_blacklisted("sub.example.com") is True


def test_fill_single_blank_slot_no_link():
    df = make_df([{"Link": "", "Person": "p"}])
    sorter = DataSorting(df)
    assert sorter._fill_single_blank_slot(0) is False


def test_find_date_with_htmldate(monkeypatch):
    df = make_df([{"Link": "http://example.com/article", "Person": "p", "Date": None}])
    sorter = DataSorting(df)

    def fake_find_date(url, outputformat=None, original_date=None):
        return "2022-01-01"

    monkeypatch.setattr('data_sorting.find_date', fake_find_date)
    assert sorter._find_date_with_htmldate(0) is True
    assert sorter.dataframe.at[0, "Date"] == "2022-01-01"
