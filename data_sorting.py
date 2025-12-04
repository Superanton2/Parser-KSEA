import pandas as pd
from htmldate import find_date
from newspaper import Article
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from openai.types.chat import ChatCompletionUserMessageParam
from openai import OpenAI

from configuration import REWRITE_NAMES, FILTER_API_KEY, blacklisted_domains, url_stop_words

class DataSorting:
    """A class for sorting and filtering a pandas DataFrame."""
    def __init__(self, dataframe: pd.DataFrame):
        """Initializes the DataSorting class with a DataFrame.

        Args:
            dataframe (pd.DataFrame): The pandas DataFrame to be processed.
        """
        self.dataframe = dataframe

        self.__filter_api_key = FILTER_API_KEY

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.__filter_api_key,
        )

        self.model = "openai/gpt-oss-20b:free"  # Безкоштовна модель

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
        """ Check if url is relevant using filters and urlparse

        Returns: Returns False if: 1. if domain is in blacklisted_domains
                                   2. if ulr is empty
                                   3. if in ulr are url_stop_words
                                   4. if in title are title_stop_words
        """

        # Handling empty values
        if not isinstance(url, str): return False

        # prepare url
        url = url.lower()

        # parse url to 6 components
        parsed_url = urlparse(url)
        # in url take domain (between https:// and the first /), lower register and delete www.
        domain = parsed_url.netloc.lower().replace('www.', '')

        # check if domain is in blacklisted_domains
        if domain in self.blacklisted_domains:
            return False

        # check if words is in url_stop_words
        for word in self.url_stop_words:
            if word in url:
                return False

        return True
        # if all is good return True


    def fill_all_blank_slots(self):
        """
        Головний метод, який запускає цикл обробки всього DataFrame.
        Він проходить по кожному рядку і викликає обробку окремого посилання.

        Returns: Returns self for method chaining
        """

        print(f"Починаємо обробку {len(self.dataframe)} посилань...")

        # Створюємо нові колонки, якщо їх немає (щоб уникнути помилок при запису)
        if 'Tittle text' not in self.dataframe.columns:
            self.dataframe['Tittle text'] = None


        # Проходимось по dataframe через iterrows, щоб мати доступ до індексу і рядка
        for index, row in self.dataframe.iterrows():
            link = row['Link']

            # Пропускаємо пусті посилання
            if pd.isna(link) or link == "":
                continue

            print(f"[{index}] Обробка: {link}")

            # Викликаємо метод обробки ОДНОГО посилання
            # Ми передаємо index, щоб всередині можна було записати результат в таблицю
            self.fill_single_blank_slot(index, link)
            print("\n\n\n")

        print("Парсинг завершено.")
        return self

    def fill_single_blank_slot(self, index, url: str):
        """

        Returns: Returns self for method chaining
        """

        print(f"обробляємо {url}")

        self._newspaper_parse(index, url)
        self._manual_parse(index, url)


        # we take only where there is a date
        present_date_mask = self.dataframe['Date'].notna()
        # we cut all existing dates to the first 10 characters
        self.dataframe.loc[present_date_mask, 'Date'] = self.dataframe.loc[present_date_mask, 'Date'].str[:10]

        return self


    def _newspaper_parse(self, index, url: str) -> bool:
        """

        :param index:
        :param url:
        :return:
        """

        print("newspaper\n\n")
        try:
            article = Article(url)
            article.download()  # 1. Завантажує HTML сторінки

            article.parse()  # 2. Парсить HTML і витягує текст
        except Exception as E:
            print(E)
            return False


        if article.text:
            self.dataframe.at[index, "Tittle text"] = article.text[:1500]


        # якщо поста дата і ми знайшли нову, то зберігаємо її
        if article.publish_date and pd.isna(self.dataframe['Date'][index]):
            self.dataframe.at[index, "Date"] = article.publish_date

        return True


    def _manual_parse(self, index, url: str) -> bool:
        """ Clear publication dates

        If there is publication date this method removes redundant information and makes it into format YYYY-MM-DD
        If there isn't publication date, then this method finds the value using module find_date from htmldate


        """
        print("manual\n\n")

        # якщо нема дати, то знайти
        if not self.dataframe['Date'][index]:
            self._find_single_date(index, url)


        # response = requests.get(url)
        # soup = BeautifulSoup(response.text, 'lxml')
        return True



    def _find_single_date(self, index, url: str) -> bool:

        # print("find date\n\n")


        # if no link, skip
        if pd.isna(self.dataframe['Link'][index]):
            return False

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




    # AI
    # def apply_ai_filtering(self):
    #       atlas-cloud/fp8
    #     # AI чистка через OpenRouter
    #     if not self.dataframe.empty:
    #         print("2. Запуск AI аналізу через OpenRouter...")
    #         ai_filter = AIFilter()
    #
    #         mask = self.dataframe.apply(
    #             lambda row: ai_filter.is_relevant_content(row.get('Link', '')),
    #             axis=1
    #         )
    #
    #         initial_count = len(self.dataframe)
    #
    #         self.dataframe = self.dataframe[mask]
    #         print(f"AI відсіяв ще {initial_count - len(self.dataframe)} статей.")
    #
    #     return self