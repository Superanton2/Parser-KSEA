import pandas as pd
from urllib.parse import urlparse

from htmldate import find_date
from newspaper import Article
import requests
from bs4 import BeautifulSoup

from configuration import REWRITE_NAMES, blacklisted_domains, url_stop_words

class DataSorting:
    """A class for sorting and filtering a pandas DataFrame."""
    def __init__(self, dataframe: pd.DataFrame):
        """Initializes the DataSorting class with a DataFrame and other parameters.

        Args:
            dataframe (pd.DataFrame): The pandas DataFrame to be processed.
        """
        self.dataframe = dataframe

        self.blacklisted_domains = blacklisted_domains
        self.url_stop_words = url_stop_words


    def sort_by_column(self, column_name, ascending=True, inplace=True):
        """Sorts the DataFrame by a single specified column.

        Args:
            column_name (str): The name of the column to sort by.
            ascending (bool, optional): Sort ascending vs. descending. Defaults to True.
            inplace (bool, optional): If True, modifies the DataFrame in place.
                                      If False, returns a new sorted DataFrame.
                                      Defaults to True.

        Returns:
            DataSorting or pd.DataFrame: Returns self for method chaining if inplace is True,
                                         otherwise returns a new sorted DataFrame.

        Raises:
            ValueError: If `column_name` does not exist in the DataFrame.
        """
        if column_name not in self.dataframe.columns:
            raise ValueError(f"Column '{column_name}' does not exist in the DataFrame.")

        if inplace:
            self.dataframe = self.dataframe.sort_values(by=column_name, ascending=ascending)
            return self
        else:
            return self.dataframe.sort_values(by=column_name, ascending=ascending)

    def sort_by_multiple_columns(self, columns, ascending=True, inplace=True):
        """Sorts the DataFrame by a list of columns.

        Args:
            columns (list[str]): A list of column names to sort by.
            ascending (bool or list[bool], optional): Sort ascending vs. descending.
                Apply to all columns if bool. Defaults to True.
            inplace (bool, optional): If True, modifies the DataFrame in place.
                                      If False, returns a new sorted DataFrame.
                                      Defaults to True.

        Returns:
            DataSorting or pd.DataFrame: Returns self for method chaining if inplace is True,
                                         otherwise returns a new sorted DataFrame.

        Raises:
            ValueError: If any column in `columns` does not exist in the DataFrame.
        """
        for column in columns:
            if column not in self.dataframe.columns:
                raise ValueError(f"Column '{column}' does not exist in the DataFrame.")

        if inplace:
            self.dataframe = self.dataframe.sort_values(by=columns, ascending=ascending)
            return self
        else:
            return self.dataframe.sort_values(by=columns, ascending=ascending)

    def remove_by_links(self, links: list, inplace=True):
        """Removes rows from the DataFrame based on a list of link substrings.

        This method filters out rows where the 'Link' column contains any of the
        substrings provided in the `links` list.

        Args:
            links (list[str]): A list of strings to search for in the 'Link' column.
                               Rows containing any of these strings will be removed.
            inplace (bool, optional): If True, modifies the DataFrame in place.
                                      If False, returns a new filtered DataFrame.
                                      Defaults to True.

        Returns:
            DataSorting or pd.DataFrame: Returns self for method chaining if inplace is True,
                                         otherwise returns a new filtered DataFrame.
        """
        if inplace:
            pattern = '|'.join(links)
            self.dataframe = self.dataframe[~self.dataframe['Link'].str.contains(pattern, na=False)]
            return self
        else:
            pattern = '|'.join(links)
            filtered_df = self.dataframe[~self.dataframe['Link'].str.contains(pattern, na=False)]
            return filtered_df

    def rename_person(self):
        """Rewrite names using keys from the configuration

        take dict from the configuration file
        and rewrite only those values in Person which ase in dict.keys

        Returns: Returns self for method chaining
        """
        # replaces names on the table using configuration file
        self.dataframe['Person'] = self.dataframe['Person'].replace(REWRITE_NAMES)

        return self

    def remove_duplicates(self):
        """Deletes duplicates from column Link

        if in column Link there is same link this method removes second duplicate
        Returns: Returns self for method chaining
        """
        # deleting duplicates
        self.dataframe = self.dataframe.drop_duplicates(subset=['Link'], keep='first')

        return self

    def apply_url_filter(self):
        """
        Applies advanced filtering based on domains, URL keywords, and Titles.
        Uses the logic from filters.py

        Returns: Returns self for method chaining
        """
        initial_count = len(self.dataframe)

        # Використовуємо apply, щоб перевірити кожен рядок (посилання + заголовок)
        # axis=1 означає, що ми йдемо по рядках

        # make mask with relevant urls
        mask = self.dataframe.apply(
            lambda row: self._check_relevance(row['Link']),
            axis=1
        )

        self.dataframe = self.dataframe[mask]

        removed_count = initial_count - len(self.dataframe)
        print(f"Url filter removed {removed_count} irrelevant links.")
        return self

    def _check_relevance(self, url: str) -> bool:
        """ Check if url is relevant using filters and urlparse.

        Returns: Returns False if: 1. if domain is in blacklisted_domains
                                   2. if ulr is empty
                                   3. if in ulr are url_stop_words
                                   4. if in title are title_stop_words
        """

        # Handling empty values
        if not isinstance(url, str): return False

        # prepare url and parse it to 6 components
        url = url.lower()
        parsed_url = urlparse(url)

        # in url take domain (between https:// and the first /), lower register and delete www.
        domain = parsed_url.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]



        # check if domain or it part is in blacklisted_domains
        for blocked_domain in self.blacklisted_domains:
            if domain == blocked_domain or domain.endswith("." + blocked_domain) or domain.startswith(blocked_domain + "."):
                return False


        if domain in self.blacklisted_domains:
            return False

        # check if words is in url_stop_words
        for word in self.url_stop_words:
            if word in url:
                return False

        return True
        # if all is good return True

    def fill_all_blank_slots(self):
        """Fill maximum possible for whole dataframe.

        This method creates new colum in dataframe named 'Tittle text'.
        this column is for ai_filter to better understand the meaning of the page

        Also, this method iterates through every row, performs a fill_single_blank_slot for each one

        Returns: Returns self for method chaining
        """

        print(f"We start processing {len(self.dataframe)} links...")

        # create new colum 'Tittle text'
        if 'Tittle text' not in self.dataframe.columns:
            self.dataframe['Tittle text'] = None


        # iterates through every row
        for index, row in self.dataframe.iterrows():
            link = row['Link']
            print(f"[{index}]: {link}")

            # use fill_single_blank_slot
            self.fill_single_blank_slot(index)

        print("Filling blank slots if finished")
        return self

    def fill_single_blank_slot(self, index):
        """Fill maximum possible for row with input index

        If there isn't link for this index, skip

        If there is publication date this method removes redundant information and makes it into format YYYY-MM-DD
        Returns: Returns self for method chaining
        """
        # if no link, skip
        if pd.isna(self.dataframe['Link'][index]) or self.dataframe['Link'][index] == "":
            print("there is no value in Link for this index")
            return False


        self._newspaper_parse(index)
        self._requests_parse(index)

        if pd.notna(self.dataframe.at[index, 'Date']):
            self.dataframe.at[index, 'Date'] = str(self.dataframe.at[index, 'Date'])[:10]

        return self

    def _newspaper_parse(self, index, max_text_save_len: int = 1500) -> bool:
        """Fill blank slots by the inputted index using module newspaper

        This helper method attempts to find information for blank slots

            1. If there isn't publication date, this method attempts to find value using newspaper
            2. If there isn't Tittle text, this method attempts to find value using newspaper

        :param index: index of row were to use this method
        :param max_text_save_len: max len(characters) of the text from article.
                                  Defaults to 100
        :return: True if all was good
                 False if we got an error during the search
        """
        url = self.dataframe['Link'][index]

        # try to parse url
        try:
            article = Article(url)
            article.download()

            article.parse()
        except Exception as E:
            print(E)
            return False

        # if there is text, save
        if article.text:
            self.dataframe.at[index, "Tittle text"] = article.text[:max_text_save_len]


        # if date is empty and new one if founded, save
        if article.publish_date and pd.isna(self.dataframe['Date'][index]):
            self.dataframe.at[index, "Date"] = article.publish_date

        return True

    def _requests_parse(self, index, max_text_save_len: int = 1500) -> bool:
        """Fill blank slots by the inputted index using requests.

        This helper method attempts to find information for blank slots
            1. If there isn't publication date, this method attempts to find value using method _find_single_date
            2. If there isn't Tittle text, this method attempts to find value using requests and BeautifulSoup

        if there were Exception during attempt of finding Tittle text, this method will return False

        :param index: index of row were to use this method
        :param max_text_save_len: max len(characters) of the text from article.
                                  Defaults to 100
        :return: True if all was good
                 False if we got an error during the search
        """

        url = self.dataframe['Link'][index]

        # If there isn't publication date use _find_single_date
        if pd.isna(self.dataframe['Date'][index]):
            self._find_single_date(index)


        # If there isn't Tittle text, attempts to find
        if pd.isna(self.dataframe['Tittle text'][index]):

            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'lxml')
                article_text = soup.get_text()

            except Exception as E:
                print(E)
                return False

            # if there are, then we save max_text_save_len of characters
            clean_article_text = " ".join(article_text.split())
            self.dataframe.at[index, "Tittle text"] = clean_article_text[:max_text_save_len]

        return True

    def _find_single_date(self, index) -> bool:
        """Find publication date by the inputted index.

        This helper method attempts to find a publication date using htmldate.
        If no date is found, it returns False.

        :param index: index by which we will check the data
        :return: True if all was good
                 False if we got an error during the search
        """

        try:
            # looking for a date at the link
            found_date = find_date(self.dataframe['Link'][index], outputformat='%Y-%m-%d', original_date=True)

            if found_date:
                # write value by index in Date
                self.dataframe.at[index, 'Date'] = found_date

        except Exception as e:
            print(e)
            return False

        return True
