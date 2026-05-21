import logging
from typing import Any

import gspread
import pandas as pd
from gspread_dataframe import set_with_dataframe

logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    def __init__(self, credentials_path: str, spreadsheet_name: str):
        """Ініціалізація підключення до Google Sheets через Service Account."""
        try:
            self.gc = gspread.service_account(filename=credentials_path)
            self.sh = self.gc.open(spreadsheet_name)
            logger.info("Успішне підключення до Google Sheets: %s", spreadsheet_name)
        except Exception as e:
            logger.error("Помилка підключення до Google Sheets: %s", e)
            raise

    def get_search_queries(self) -> list[str]:
        worksheet = self.sh.worksheet("Search_Queries")
        records = worksheet.col_values(1)
        return [r.strip() for r in records[1:] if r.strip()]

    def get_blacklists(self) -> dict[str, list[str]]:
        """Читає чорні списки. Стовпець A - домени, B - стоп-слова, C - лінки для видалення."""
        worksheet = self.sh.worksheet("Blacklists")
        data = worksheet.get_all_values()

        domains, stop_words, links = [], [], []
        for row in data[1:]:  # Пропуск заголовків
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
        """Читає параметри бота зі стовпців A (Key) та B (Value)."""
        worksheet = self.sh.worksheet("Bot_Params")
        records = worksheet.get_all_records()
        params = {}
        for row in records:
            if "Key" in row and "Value" in row:
                params[row["Key"]] = row["Value"]
        return params

    def append_results(self, df: pd.DataFrame) -> None:
        """Додає нові рядки в кінець аркуша Results та створює колонку Verified."""
        worksheet = self.sh.worksheet("Results")

        if "Verified" not in df.columns:
            df.insert(0, "Verified", False)

        existing_data = worksheet.get_all_values()
        next_row = len(existing_data) + 1

        set_with_dataframe(worksheet, df, row=next_row, include_column_header=False)
        logger.info("Додано %d рядків до аркуша Results.", len(df))