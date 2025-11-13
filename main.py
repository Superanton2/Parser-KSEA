from get_links_from_serpAPI import get_links_from_serpAPI
from get_links_from_google import get_links_from_google
from data_sorting import data_sorting

from configuration import SEARCH_QUERY, SERP_API_KEY



def main(SEARCH_QUERY, SERP_API_KEY):
    """
    the main function that combines all three blocks of code together

    :param SEARCH_QUERY: enter list of people who will be searched
    :param SERP_API_KEY: enter API key so serp API can work
    :return: nothing
    """

    # search by news
    get_links_from_serpAPI(SEARCH_QUERY ,SERP_API_KEY)

    # search by google
    get_links_from_google(SEARCH_QUERY)

    # data sorting
    # not working yet
    data_sorting()


if __name__ == "__main__":
    main(SEARCH_QUERY, SERP_API_KEY)