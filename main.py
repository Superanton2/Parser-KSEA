from get_lenks_from_newsAPI import get_lenks_from_newsAPI
from get_links_from_google import get_links_from_google
from data_sorting import data_sorting

from configuration import SEARCH_QUERY, SERP_API_KEY



def main(SEARCH_QUERY, SERP_API_KEY):
    # the main function that combines all three blocks of code together


    # search by news
    get_lenks_from_newsAPI(SEARCH_QUERY ,SERP_API_KEY)

    # search by google
    get_links_from_google(SEARCH_QUERY)

    # data sorting
    # not working yet
    data_sorting()






if __name__ == "__main__":
    main(SEARCH_QUERY, SERP_API_KEY)