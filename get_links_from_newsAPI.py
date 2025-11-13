from serpapi import GoogleSearch
import csv


def serpapi_search(q: str, api_key: str) -> dict:
    """
    this function searching using serp API

    :param q: enter one query that will be searched
    :param api_key: enter API key so serp API can work
    :return: json data about query as dict
    """

    # parameters for search serp API
    params = {
        "tbm": "nws",  # tbm=nws means searching in "News"
        "q": q,  # search query
        "num": "100",  # Max number of results
        "api_key": api_key, # our API key
        "gl": "uk", # search by country
    }

    # perform request to SerpApi
    search = GoogleSearch(params)
    results_dict = search.get_dict()

    return results_dict



def prepare_csv_file(file_name: str):
    """
    this function creates new file or overwrites an existing one and adds a header there to prepare for writing data

    :param file_name: enter name of file to create
    :return: None
    """

    # creates new file or overwrites an existing one
    with open(file_name, "w", newline="") as file:

        # create header
        header = ['Person', 'Title', 'Date', 'Source', 'link']
        for item in header:
            file.write(item)
            file.write(", ")



def write_news_results(person: str, file_name: str, results_dict: dict):
    """
    this function takes the search result as dict and writes it to the file we entered

    :param person: name of person we are processing
    :param file_name: name of the file where to write values
    :param results_dict: values to be writen
    :return: None
    """

    # open existing file and appending values
    with open(file_name, "a", newline="") as file:
        writer = csv.writer(file)

        # go through each link and add data to csv file
        for news_link in results_dict['news_results']:
            # prepare a line for writing
            data_row = [
                    person,
                    news_link.get('title'),
                    news_link.get('date'),
                    news_link.get('source'),
                    news_link.get('link')
            ]
            # write to file
            writer.writerow(data_row)

        print(f"Added {len(results_dict['news_results'])} links for '{person}'")



def write_empty_results(person: str, file_name: str):
    """
    this function writes empty results in csv file

    :param person: name of person we are processing
    :param file_name: name of the file where to write values
    :return: None
    """

    with open(file_name, "a", newline="") as file:
        writer = csv.writer(file)
        # prepare a line for writing
        data_row = [
            person,
            "", # Title
            "", # Date
            "", # Source
            "", # link
        ]
        # write to file
        writer.writerow(data_row)
        print(f"No news found for {person}")



def get_links_from_serpAPI(SEARCH_QUERY: list, SERP_API_KEY: str):
    """
    this function is to search by news using serp API

    :param SEARCH_QUERY: enter list of people who will be searched
    :param SERP_API_KEY: enter API key so serp API can work
    :return: None
    """
    print("Starting searching with serp API\n")

    file_name = "serp_api_results.csv"
    prepare_csv_file(file_name)

    for person in SEARCH_QUERY:
        print(f"Searching for {person}")
        results_dict = serpapi_search(person, SERP_API_KEY)

        # check whether the results contain a 'news_results' block
        if 'news_results' in results_dict:
            write_news_results(person, file_name, results_dict)
        else:
            write_empty_results(person, file_name)



    print(f"\nAll work is complete! The results are saved to the file '{file_name}'")



