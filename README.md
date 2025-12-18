# KSE Agrocenter Publication Parser

This project is a Python-based tool designed to automate the process of finding online publications related to key personnel of the KSE Agrocenter. It utilizes the Google Custom Search API to perform targeted searches, collects the results, and organizes them into a clean, structured CSV file for easy analysis and reporting.

## Features

- **Automated Google Search**: Performs searches for a predefined list of individuals.
- **Customizable Queries**: Easily modify the list of people to search for in the `configuration.py` file.
- **Structured Output**: Saves results in a CSV file with columns: `Person`, `Title`, `Date`, `Source`, and `Link`.
- **Data Sorting**: Includes functionality to sort the collected data by any column (e.g., by `Date`).
- **Data Filtering**: Allows for the removal of irrelevant results based on URL patterns.
- **Robust & Paginated**: Handles API pagination to fetch up to 100 results per query.

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine.

### Prerequisites

- Python 3.6+
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
    Open the `configuration.py` file and replace the placeholder values with your credentials:
    ```python
    
    API_KEY = "YOUR_API_KEY_HERE"

    SEARCH_ENGINE_ID = "YOUR_SEARCH_ENGINE_ID_HERE"
    ```

3.  **Customize Search Queries (Optional):**
    You can edit the `SEARCH_QUERY` list in `configuration.py` to add, remove, or modify the names of the people you want to search for.

## Usage

To run the parser and generate the report, execute the main script from your terminal.

```bash
python main.py
```
*(Assuming you have a `main.py` that orchestrates the process)*

The script will perform the following actions:
1.  Read the search queries from `configuration.py`.
2.  Query the Google Custom Search API for each person.
3.  Print the found links to the console in real-time.
4.  Save all results into a `results.csv` file in the project's root directory.
5.  The data can then be further processed using the `DataSorting` class if needed.

## Project Structure

```
.
├── google_search_service.py  # Handles all communication with the Google Search API.
├── data_sorting.py           # Contains the class for sorting and filtering data.
├── configuration.py          # Stores API keys, search engine ID, and search queries.
├── main.py                   # The main entry point for the application (example).
└── README.md                 # This file.
```
