import pytest
from google_sheets_manager import GoogleSheetsManager

import os
from dotenv import load_dotenv
load_dotenv()

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "KSE_Agrocenter_Parser")

@pytest.fixture(scope="module")
def sheet_manager():
    """
    Initialize the connection once for all tests in this module.
    """
    manager = GoogleSheetsManager(CREDENTIALS_PATH, SPREADSHEET_NAME)
    return manager


def test_get_search_queries_returns_correct_type(sheet_manager):
    """Test the basic return types of the function."""
    queries = sheet_manager.get_search_queries()

    assert isinstance(queries, list), "The function should return a list."
    assert len(queries) > 0, "The list of queries should not be empty."
    assert all(isinstance(q, str) for q in queries), "All elements in the list must be strings."


def test_get_search_queries_includes_definitely_priority(sheet_manager):
    """
    Test if individuals with the 'Definitely' priority are included in the results.
    Data is based on rows 3 and 4 of the provided spreadsheet.
    """
    queries = sheet_manager.get_search_queries()

    for q in queries:
        print(q, end=" / ")
    assert "Oleh Nivievskyi" in queries, "English name with 'Definitely' priority not found."
    assert "Олег Нів'євський" in queries, "Ukrainian name with 'Definitely' priority not found."

    assert "Mariia Bogonos" in queries
    assert "Марія Богонос" in queries
    assert "Artur Burak" not in queries


def test_get_search_queries_excludes_optional_priority(sheet_manager):
    """
    Test if the function correctly ignores rows with 'Optional' priority.
    Data is based on rows 7, 10, and 12 of the provided spreadsheet.
    """
    queries = sheet_manager.get_search_queries()

    assert "Ivan Kolodiazhnyi" not in queries, "Optional name (Ivan Kolodiazhnyi) was included in the list!"
    assert "Іван Колодяжний" not in queries

    assert "Artur Burak" not in queries, "Optional name (Artur Burak) was included in the list!"
    assert "Hryhorii Stolnikovych" not in queries


def test_get_search_queries_no_duplicates(sheet_manager):
    """
    Test that there are no duplicates in the final list (the function should use a set).
    """
    queries = sheet_manager.get_search_queries()

    assert len(queries) == len(set(queries)), "There are duplicate queries in the final list."


def test_get_search_queries_default_behavior(sheet_manager):
    """
    Test the default behavior of the function.
    Expected: save_optional=False, save_pronounciations=False.
    It should exclude 'Optional' priorities and exclude pronunciations.
    """
    queries = sheet_manager.get_search_queries()

    # Check that definitely included members are present
    assert "Oleh Nivievskyi" in queries

    # Check that optional members are EXCLUDED
    assert "Ivan Kolodiazhnyi" not in queries
    assert "Artur Burak" not in queries

    # Check that pronunciations are EXCLUDED (Oleg Nivievskyi is a pronunciation)
    assert "Oleg Nivievskyi" not in queries


def test_get_search_queries_with_optional_true(sheet_manager):
    """
    Test the function with save_optional=True and save_pronounciations=False.
    Expected: It should INCLUDE 'Optional' priorities, but exclude pronunciations.
    """
    queries = sheet_manager.get_search_queries(save_optional=True)

    # Check that optional members are now INCLUDED
    assert "Ivan Kolodiazhnyi" in queries
    assert "Іван Колодяжний" in queries
    assert "Artur Burak" in queries

    # Check that pronunciations are still EXCLUDED
    assert "Oleg Nivievskyi" not in queries


def test_get_search_queries_with_pronunciations_true(sheet_manager):
    """
    Test the function with save_optional=False and save_pronounciations=True.
    Expected: It should EXCLUDE 'Optional' priorities, but include pronunciations.
    """
    queries = sheet_manager.get_search_queries(save_pronounciations=True)

    # Check that optional members are still EXCLUDED
    assert "Ivan Kolodiazhnyi" not in queries

    # Check that pronunciations are now INCLUDED
    assert "Oleg Nivievskyi" in queries

    # Check multiple pronunciations for Mariia Bogonos (Row 4)
    assert "Maria Bogonos" in queries
    assert "Marija Bogonos" in queries


def test_get_search_queries_all_options_true(sheet_manager):
    """
    Test the function with both parameters set to True.
    Expected: It should INCLUDE 'Optional' priorities AND include pronunciations.
    """
    queries = sheet_manager.get_search_queries(save_optional=True, save_pronounciations=True)

    # Check definitely included members
    assert "Oleh Nivievskyi" in queries

    # Check optional members
    assert "Ivan Kolodiazhnyi" in queries
    assert "Artur Burak" in queries

    # Check pronunciations
    assert "Oleg Nivievskyi" in queries
    assert "Maria Bogonos" in queries