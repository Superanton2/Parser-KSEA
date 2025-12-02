from urllib.parse import urlparse
from configuration import blacklisted_domains, url_stop_words, title_stop_words

class LinkFilter:
    def __init__(self):
        """Initializes the LinkFilter class with a filters.
        filters are from configuration file
        """

        self.blacklisted_domains = blacklisted_domains
        self.url_stop_words = url_stop_words
        self.title_stop_words = title_stop_words


    def is_relevant(self, url: str, title: str) -> bool:
        """ Check if url is relevant using filters


        Перевіряє URL і Заголовок. Повертає True, якщо посилання корисне.
        Returns: Returns False if: 1. if domain is in blacklisted_domains
                                   2. if ulr is empty
                                   3. if in ulr are url_stop_words
                                   4. if in title are title_stop_words

        """
        # Handling empty values
        if not isinstance(url, str): return False

        # prepare url and title
        url = url.lower()
        if title:
            title = str(title).lower()
        else:
            ""


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

        # check if words in title is in title_stop_words
        for word in self.title_stop_words:
            if word in title:
                return False

        return True
        # if all is good return True
