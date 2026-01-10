# KSE Agrocenter Publication Parser

This project is a Python-based tool designed to automate the process of finding online publications related to key personnel of the KSE Agrocenter. It utilizes the Google Custom Search API to perform targeted searches, collects the results, and organizes them into a clean, structured CSV file for easy analysis and reporting.

## Features

- **Automated Google Search**: Performs searches for a predefined list of individuals.
- **Customizable Queries**: Easily modify the list of people to search for in the `configuration.py` file.
- **Date range filtering**: Optionally restrict results to a specific time window via `date_from` and `date_to`.
- **Structured Output**: Saves results in a CSV file with columns: `Person`, `Title`, `Date`, `Source`, and `Link`.
- **Data Sorting**: Includes functionality to sort the collected data by any column (e.g., by `Date`).
- **Data Filtering**: Allows for the removal of irrelevant results based on URL patterns.
- **Robust & Paginated**: Handles API pagination to fetch up to 100 results per query.

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine.

### Prerequisites

- Python 3.10+
- Pip (Python package installer)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Superanton2/Parser-KSEA.git
    cd Parser-KSEA
    ```

2.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

Before running the script, you need to configure your API credentials and search parameters.

1.  **Obtain API Credentials:**
    - **API Key**: Get a Google API Key from the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
    - **Search Engine ID**: Create a Custom Search Engine and get its ID from the [Control Panel](https://cse.google.com/). Make sure to configure it to search the entire web.

2.  **Update `configuration.py`:**
    Open the `configuration.py` file and set values in `SearchConfig()`. Because this dataclass is frozen, you should pass the values when creating it, for example:
    ```python
    # configuration.py
    from dataclasses import dataclass
    from pathlib import Path
    from typing import Final

    @dataclass(frozen=True)
    class SearchConfig:
        api_key: str = "YOUR_API_KEY_HERE"
        search_engine_id: str = "YOUR_SEARCH_ENGINE_ID_HERE"
        max_results: int = 100
        sort_by_date: bool = True
        region: str = "ua"
        date_from: str | None = "2024-01-01"  # or "20240101"
        date_to: str | None = "2024-12-31"    # or "20241231"

    SEARCH_CONFIG: Final = SearchConfig()
    ```

    Notes:
    - If both `date_from` and `date_to` are provided, results are filtered using Google's CSE `sort` range: `date:r:YYYYMMDD:YYYYMMDD`.
    - If only `date_from` is set, `date_to` defaults to today (UTC).
    - If only `date_to` is set, `date_from` defaults to `1970-01-01`.
    - If neither is provided, and `sort_by_date=True`, results are sorted by date without filtering.

3.  **Customize Search Queries (Optional):**
    You can edit the `SEARCH_QUERY` list in `configuration.py` to add, remove, or modify the names of the people you want to search for.

## Usage

To run the parser and generate the report, execute the main script from your terminal.

```bash
python main.py
```

The script will perform the following actions:
1.  Read the search queries from `configuration.py`.
2.  Query the Google Custom Search API for each person.
3.  Print the found links to the console in real-time.
4.  Save all results into the CSV specified by `OUTPUT_CONFIG.search_results_csv`.
5.  Process and produce a sorted CSV specified by `OUTPUT_CONFIG.sorted_results_csv`.

## Project Structure

```
.
├── google_search_service.py  # Handles all communication with the Google Search API.
├── data_sorting.py           # Contains the class for sorting and filtering data.
├── configuration.py          # Stores API keys, search engine ID, and search queries.
├── main.py                   # The main entry point for the application.
└── README.md                 # This file.
```
