from __future__ import annotations

from typing import Self
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from htmldate import find_date
from newspaper import Article

from configuration import REWRITE_NAMES, BLACKLISTED_DOMAINS, URL_STOP_WORDS
from llm import LLM


class DataSorting:
    """A class for sorting and filtering a pandas DataFrame of search results."""

    # Column names as constants
    COL_LINK = "Link"
    COL_PERSON = "Person"
    COL_DATE = "Date"
    COL_TITLE_TEXT = "Title text"

    # Default settings
    DEFAULT_MAX_TEXT_LENGTH = 1500

    def __init__(
            self,
            dataframe: pd.DataFrame,
            blacklisted_domains: list[str] | None = None,
            url_stop_words: list[str] | None = None,
    ) -> None:
        """Initialize the DataSorting class with a DataFrame and filter settings.

        Args:
            dataframe: The pandas DataFrame to be processed.
            blacklisted_domains: Domains to filter out. Uses config default if None.
            url_stop_words: URL keywords to filter out. Uses config default if None.
        """
        self.dataframe = dataframe
        self.blacklisted_domains = blacklisted_domains or BLACKLISTED_DOMAINS
        self.url_stop_words = url_stop_words or URL_STOP_WORDS

    def sort_by_column(
            self,
            column_name: str,
            ascending: bool = True,
            inplace: bool = True,
    ) -> Self | pd.DataFrame:
        """Sort the DataFrame by a single specified column.

        Args:
            column_name: The name of the column to sort by.
            ascending: Sort ascending vs. descending. Defaults to True.
            inplace: If True, modifies the DataFrame in place.
                     If False, returns a new sorted DataFrame.

        Returns:
            Self for method chaining if inplace is True,
            otherwise returns a new sorted DataFrame.

        Raises:
            ValueError: If column_name does not exist in the DataFrame.
        """
        if column_name not in self.dataframe.columns:
            raise ValueError(f"Column '{column_name}' does not exist in the DataFrame.")

        sorted_df = self.dataframe.sort_values(by=column_name, ascending=ascending)

        if inplace:
            self.dataframe = sorted_df
            return self
        return sorted_df

    def sort_by_multiple_columns(
            self,
            columns: list[str],
            ascending: bool | list[bool] = True,
            inplace: bool = True,
    ) -> Self | pd.DataFrame:
        """Sort the DataFrame by multiple columns.

        Args:
            columns: A list of column names to sort by.
            ascending: Sort ascending vs. descending.
                       Apply to all columns if bool.
            inplace: If True, modifies the DataFrame in place.

        Returns:
            Self for method chaining if inplace is True,
            otherwise returns a new sorted DataFrame.

        Raises:
            ValueError: If any column does not exist in the DataFrame.
        """
        missing_cols = [col for col in columns if col not in self.dataframe.columns]
        if missing_cols:
            raise ValueError(f"Columns {missing_cols} do not exist in the DataFrame.")

        sorted_df = self.dataframe.sort_values(by=columns, ascending=ascending)

        if inplace:
            self.dataframe = sorted_df
            return self
        return sorted_df

    def remove_by_links(
            self,
            links: list[str],
            inplace: bool = True,
    ) -> Self | pd.DataFrame:
        """Remove rows containing specified link substrings.

        Args:
            links: Substrings to search for in the 'Link' column.
                   Rows containing any of these strings will be removed.
            inplace: If True, modifies the DataFrame in place.

        Returns:
            Self for method chaining if inplace is True,
            otherwise returns a new filtered DataFrame.
        """
        pattern = "|".join(links)
        filtered_df = self.dataframe[
            ~self.dataframe[self.COL_LINK].str.contains(pattern, na=False)
        ]

        if inplace:
            self.dataframe = filtered_df
            return self
        return filtered_df

    def rename_person(self) -> Self:
        """Normalize person names using the configuration mapping.

        Uses REWRITE_NAMES from configuration to standardize names
        (e.g., Ukrainian to English transliteration).

        Returns:
            Self for method chaining.
        """
        self.dataframe[self.COL_PERSON] = self.dataframe[self.COL_PERSON].replace(
            REWRITE_NAMES
        )
        return self

    def remove_duplicates(self) -> Self:
        """Remove duplicate entries based on the Link column.

        Keeps the first occurrence of each unique link.

        Returns:
            Self for method chaining.
        """
        self.dataframe = self.dataframe.drop_duplicates(
            subset=[self.COL_LINK], keep="first"
        )
        return self

    def apply_url_filter(self) -> Self:
        """Apply URL-based filtering to remove irrelevant results.

        Filters out URLs from blacklisted domains and those containing
        stop words.

        Returns:
            Self for method chaining.
        """
        initial_count = len(self.dataframe)

        mask = self.dataframe[self.COL_LINK].apply(self._check_relevance)
        self.dataframe = self.dataframe[mask]

        removed_count = initial_count - len(self.dataframe)
        print(f"URL filter removed {removed_count} irrelevant links.")
        return self

    def _check_relevance(self, url: str) -> bool:
        """Check if a URL is relevant based on domain and keyword filters.

        Args:
            url: The URL to check.

        Returns:
            True if the URL is relevant, False if it should be filtered out.
        """
        if not isinstance(url, str):
            return False

        url_lower = url.lower()
        parsed_url = urlparse(url_lower)

        # Extract and normalize domain
        domain = parsed_url.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        # Check against blacklisted domains
        if self._is_domain_blacklisted(domain):
            return False

        # Check for stop words in URL
        if any(word in url_lower for word in self.url_stop_words):
            return False

        return True

    def _is_domain_blacklisted(self, domain: str) -> bool:
        """Check if a domain matches any blacklisted domain pattern.

        Args:
            domain: The domain to check (without www prefix).

        Returns:
            True if the domain is blacklisted.
        """
        for blocked_domain in self.blacklisted_domains:
            if (
                    domain == blocked_domain
                    or domain.endswith(f".{blocked_domain}")
                    or domain.startswith(f"{blocked_domain}.")
            ):
                return True
        return False

    def fill_all_blank_slots(self) -> Self:
        """Fill missing data for all rows in the DataFrame.

        Creates a 'Title text' column and attempts to fill missing dates
        and article text for each row.

        Returns:
            Self for method chaining.
        """
        print(f"Processing {len(self.dataframe)} links...")

        if self.COL_TITLE_TEXT not in self.dataframe.columns:
            self.dataframe[self.COL_TITLE_TEXT] = None

        for index, row in self.dataframe.iterrows():
            link = row[self.COL_LINK]
            print(f"[{index}]: {link}")
            self._fill_single_blank_slot(index)

        print("Filling blank slots completed.")
        return self

    def apply_ai_filter(self) -> None:
        llm = LLM(model_name="openai/gpt-oss-safeguard-20b:groq")
        for article in self.dataframe["Title text"]:
            if pd.isna(article):
                continue
            is_article = llm.is_article(article)
            if not is_article:
                self.dataframe = self.dataframe[self.dataframe["Title text"] != article]

    def _fill_single_blank_slot(self, index: int) -> bool:
        """Fill missing data for a single row.

        Attempts to find publication date and article text using
        various parsing methods.

        Args:
            index: The DataFrame row index to process.

        Returns:
            True if processing was successful, False otherwise.
        """
        link = self.dataframe.at[index, self.COL_LINK]

        if pd.isna(link) or link == "":
            print("No link value for this index")
            return False

        self._parse_with_newspaper(index)
        self._parse_with_requests(index)

        # Normalize date format to YYYY-MM-DD
        if pd.notna(self.dataframe.at[index, self.COL_DATE]):
            self.dataframe.at[index, self.COL_DATE] = str(
                self.dataframe.at[index, self.COL_DATE]
            )[:10]

        return True

    def _parse_with_newspaper(
            self,
            index: int,
            max_text_length: int = DEFAULT_MAX_TEXT_LENGTH,
    ) -> bool:
        """Extract article data using the newspaper library.

        Args:
            index: The DataFrame row index to process.
            max_text_length: Maximum characters to save from article text.

        Returns:
            True if parsing was successful, False otherwise.
        """
        url = self.dataframe.at[index, self.COL_LINK]

        try:
            article = Article(url)
            article.download()
            article.parse()
        except Exception as e:
            print(f"Newspaper parsing error: {e}")
            return False

        if article.text:
            self.dataframe.at[index, self.COL_TITLE_TEXT] = article.text[:max_text_length]

        if article.publish_date and pd.isna(self.dataframe.at[index, self.COL_DATE]):
            self.dataframe.at[index, self.COL_DATE] = article.publish_date

        return True

    def _parse_with_requests(
            self,
            index: int,
            max_text_length: int = DEFAULT_MAX_TEXT_LENGTH,
    ) -> bool:
        """Extract article data using requests and BeautifulSoup.

        Args:
            index: The DataFrame row index to process.
            max_text_length: Maximum characters to save from article text.

        Returns:
            True if parsing was successful, False otherwise.
        """
        url = self.dataframe.at[index, self.COL_LINK]

        # Try to find date if missing
        if pd.isna(self.dataframe.at[index, self.COL_DATE]):
            self._find_date_with_htmldate(index)

        # Try to get article text if missing
        if pd.isna(self.dataframe.at[index, self.COL_TITLE_TEXT]):
            try:
                response = requests.get(url, timeout=10)
                soup = BeautifulSoup(response.text, "lxml")
                article_text = soup.get_text()
                clean_text = " ".join(article_text.split())
                self.dataframe.at[index, self.COL_TITLE_TEXT] = clean_text[:max_text_length]
            except Exception as e:
                print(f"Requests parsing error: {e}")
                return False

        return True

    def _find_date_with_htmldate(self, index: int) -> bool:
        """Find publication date using htmldate library.

        Args:
            index: The DataFrame row index to process.

        Returns:
            True if date was found, False otherwise.
        """
        try:
            url = self.dataframe.at[index, self.COL_LINK]
            found_date = find_date(
                url,
                outputformat="%Y-%m-%d",
                original_date=True,
            )

            if found_date:
                self.dataframe.at[index, self.COL_DATE] = found_date
                return True

        except Exception as e:
            print(f"Date finding error: {e}")

        return False
