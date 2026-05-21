import logging
from typing import Any
import gspread
import pandas as pd
from gspread_dataframe import set_with_dataframe

logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    def __init__(self, credentials_path: str, spreadsheet_name: str):
        """
        Initialize connection to Google Sheets via Service Account.

        Args:
            credentials_path (str): Path to the JSON key file for the service account.
            spreadsheet_name (str): Name of the target Google Spreadsheet document.

        Returns:
            None
        """
        try:
            self.gc = gspread.service_account(filename=credentials_path)
            self.sh = self.gc.open(spreadsheet_name)
            logger.info("Successfully connected to Google Sheets: %s", spreadsheet_name)
        except Exception as e:
            logger.error("Failed to connect to Google Sheets: %s", e)
            raise


    def get_search_queries(self, save_optional= False, save_pronounciations= False) -> list[str]:
        """
        Fetches unique search terms from the 'Search_Queries' worksheet.

        Args:
            save_optional (bool): Include members with 'Optional' priority.
            save_pronounciations (bool): Include alternative name spellings.

        Returns:
            list[str]: List of unique search queries.
        """
        worksheet = self.sh.worksheet("Search_Queries")
        data = worksheet.get_all_values()

        if not data:
            return []

        headers = data[0]
        records = [dict(zip(headers, row)) for row in data[1:]]
        queries = set()

        for row in records:
            self._process_one_row_from_records(row, save_optional, save_pronounciations, queries)
        return list(queries)

    def _process_one_row_from_records(self, row, save_optional, save_pronounciations, queries):
        """
        Processes a single row and adds valid names to the queries set.

        Args:
            row (dict): Dictionary containing row data.
            save_optional (bool): Flag to include 'Optional' priority rows.
            save_pronounciations (bool): Flag to include alternative spellings.
            queries (set): Target set updated with discovered names.
        """
        priority = str(row.get("Priority", "")).strip().lower()
        if not save_optional and (priority == "optional"):
            return

        eng_name = str(row.get("Member ENG", "")).strip()
        ukr_name = str(row.get("Member UKR", "")).strip()
        pronunciations_raw = str(row.get("Pronounciations", "")).strip()

        if eng_name:
            queries.add(eng_name)
        if ukr_name:
            queries.add(ukr_name)
        if save_pronounciations and pronunciations_raw:
            parts = [p.strip() for p in pronunciations_raw.split(",") if p.strip()]
            for part in parts:
                cleaned_part = part.strip(",\"")
                if cleaned_part:
                    queries.add(cleaned_part)

    def get_blacklists(self) -> dict[str, list[str]]:
        """
        Read domain and keyword blacklists from the 'Blacklists' worksheet.

        Args:
            None

        Returns:
            dict[str, list[str]]: A dictionary containing lists for 'domains',
                'stop_words', and 'links_to_remove'.
        """
        worksheet = self.sh.worksheet("Blacklists")
        data = worksheet.get_all_values()

        domains, stop_words, links = [], [], []
        for row in data[1:]:
            if len(row) > 0 and row[0].strip():
                domains.append(row[0].strip())
            if len(row) > 1 and row[1].strip():
                stop_words.append(row[1].strip())
            if len(row) > 2 and row[2].strip():
                links.append(row[2].strip())

        return {
            "domains": domains,
            "stop_words": stop_words,
            "links_to_remove": links
        }

    def get_bot_params(self) -> dict[str, Any]:
        """
        Read runtime configuration key-value pairs from 'Bot_Params' worksheet.

        Args:
            None

        Returns:
            dict[str, Any]: Key-value configuration parameters.
        """


        worksheet = self.sh.worksheet("Bot_Params")
        data = worksheet.get_all_values()

        if not data:
            return {}

        headers = data[0]
        records = [dict(zip(headers, row)) for row in data[1:]]
        params = {}

        for row in records:
            if "Key" in row and "Value" in row and row["Key"].strip():
                params[row["Key"]] = row["Value"]
        return params

    def append_results(self, df: pd.DataFrame) -> None:
        """
        Append processed search result records to the end of 'Results' worksheet.

        Inserts a 'Verified' column at the beginning if not already present.

        Args:
            df (pd.DataFrame): Sorted data containing news mentions.

        Returns:
            None
        """
        worksheet = self.sh.worksheet("Results")

        if "Verified" not in df.columns:
            df.insert(0, "Verified", False)

        existing_data = worksheet.get_all_values()
        next_row = len(existing_data) + 1

        set_with_dataframe(worksheet, df, row=next_row, include_column_header=False)
        logger.info("Successfully appended %d rows to the 'Results' sheet.", len(df))