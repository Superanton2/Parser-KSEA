import pandas as pd
from htmldate import find_date
from configuration import REWRITE_NAMES

class DataSorting:
    """A class for sorting and filtering a pandas DataFrame."""
    def __init__(self, dataframe: pd.DataFrame):
        """Initializes the DataSorting class with a DataFrame.

        Args:
            dataframe (pd.DataFrame): The pandas DataFrame to be processed.
        """
        self.dataframe = dataframe

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


    def clean_dates(self):
        """ Clear publication dates

        If there is publication date this method removes redundant information and makes it into format YYYY-MM-DD
        If there isn't publication date, then this method finds the value using module find_date from htmldate

        Returns: Returns self for method chaining
        """

        # we take only where there is a date
        present_date_mask = self.dataframe['Date'].notna()
        # we cut all existing dates to the first 10 characters
        self.dataframe.loc[present_date_mask, 'Date'] = self.dataframe.loc[present_date_mask, 'Date'].str[:10]


        # now we take only where there are no date
        missing_date_mask = self.dataframe['Date'].isna()

        print("Looking for dates...")
        for index, row in self.dataframe[missing_date_mask].iterrows():
            print(f"{index}/{len(self.dataframe['Date'])}  - {self.dataframe['Date'][index]}")

            # relevant link
            link = row['Link']

            # if no link, skip
            if pd.isna(link):
                continue

            try:
                # looking for a date at the link
                found_date = find_date(link, outputformat='%Y-%m-%d', original_date=True)

                if found_date:
                    # write value by index in Date
                    self.dataframe.at[index, 'Date'] = found_date

            except Exception as e:
                print(e)

        return self


    def remove_duplicates(self):
        """Deletes duplicates from column Link

        if in column Link there is same link this method removes second duplicate
        Returns: Returns self for method chaining
        """
        # deleting duplicates
        self.dataframe = self.dataframe.drop_duplicates(subset=['Link'], keep='first')

        return self


    def rename_all(self):
        """Rewrite names using keys from the configuration

        take dict from the configuration file
        and rewrite only those values in Person which ase in dict.keys

        Returns: Returns self for method chaining
        """
        # replaces names on the table using configuration file
        self.dataframe['Person'] = self.dataframe['Person'].replace(REWRITE_NAMES)

        return self
