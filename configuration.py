from dataclasses import dataclass
from pathlib import Path
from typing import Final
import os

HF_API_KEY: Final[str] = os.getenv("")

@dataclass(frozen=True)
class SearchConfig:
    """Configuration for Google Custom Search API."""
    api_key: str = "API KEY FROM https://console.cloud.google.com/apis/credentials"
    search_engine_id: str = "SEARCH ENGINE ID FROM https://cse.google.com/"
    max_results: int = 100
    sort_by_date: bool = True
    region: str = "ua"


@dataclass(frozen=True)
class OutputConfig:
    """Configuration for output files."""
    output_dir: Path = Path(".")
    search_results_csv: str = "google_search_results.csv"
    sorted_results_csv: str = "google_links_sorted.csv"
    links_txt: str = "google_links.txt"

    @property
    def search_results_path(self) -> Path:
        return self.output_dir / self.search_results_csv

    @property
    def sorted_results_path(self) -> Path:
        return self.output_dir / self.sorted_results_csv

    @property
    def links_path(self) -> Path:
        return self.output_dir / self.links_txt


# Default configurations
SEARCH_CONFIG: Final = SearchConfig()
OUTPUT_CONFIG: Final = OutputConfig()

# Legacy compatibility
API_KEY: Final[str] = SEARCH_CONFIG.api_key
SEARCH_ENGINE_ID: Final[str] = SEARCH_CONFIG.search_engine_id

SEARCH_QUERY: Final[list[str]] = [
    "Center for Food and Land Use Research (KSE Agrocenter)",
    "Агроцентр KSE",

    "Oleg Nivievskyi",
    "Oleh Nivievskyi",
    "Олег Нів’євський",

    "Mariia Bogonos",
    "Марія Богонос",

    "Pavlo Martyshev",
    "Павло Мартишев",

    "Valentyn Litvinov",
    "Валентин Літвінов",

    "Ivan Kolodiazhnyi",
    "Іван Колодяжний",

    "Ellina Iurchenko",
    "Елліна Юрченко",

    "Roksolana Nazarkina",
    "Роксолана Назаркіна",

    "Hryhorii Stolnikovych",
    "Григорій Стольнікович",

    "Roman Neyter",
    "Роман Нейтер",

    "Igor Piddubnyi",
    "Ігор Піддубний",

    "Дмитро Душко",
    "Dmytro Dushko",

    "Artur Burak",
    "Артур Бурак",

    "Dmytro Tеslеnko",
    "Дмитро Тесленко",
]

REWRITE_NAMES: Final[dict[str, str]] = {
    "Center for Food and Land Use Research (KSE Agrocenter)" : "KSE Agrocenter",
    "Агроцентр KSE" : "KSE Agrocenter",
    "Oleg Nivievskyi" : "Oleh Nivievskyi",
    "Олег Нів’євський" : "Oleh Nivievskyi",
    "Марія Богонос" : "Mariia Bogonos",
    "Павло Мартишев" : "Pavlo Martyshev",
    "Валентин Літвінов" : "Valentyn Litvinov",
    "Іван Колодяжний" : "Ivan Kolodiazhnyi",
    "Елліна Юрченко" : "Ellina Iurchenko",
    "Роксолана Назаркіна" : "Roksolana Nazarkina",
    "Артур Бурак" : "Artur Burak",
    "Дмитро Тесленко" : "Dmytro Tеslеnko",
    "Дмитро Душко" : "Dmytro Dushko",
    "Григорій Стольнікович" : "Hryhorii Stolnikovych",
    "Роман Нейтер" : "Roman Neyter",
    "Ігор Піддубний" : "Igor Piddubnyi",
}

BLACKLISTED_DOMAINS: Final[list[str]] = [
    "kse.ua", "vk.com", "facebook.com", "linkedin.com", "instagram.com", "opendatabot.ua", "t.me",
    "tiktok.com", "letterboxd.com", "goodreads.com", "scholar.google.com", "academia.edu", "scribd.com",
    "journals.sagepub.com", "freepolicybriefs.org",
    "youcontrol.com", "swrailway.gov.ua", "sinoptik.ua", "gismeteo.ua", "agroberichtenbuitenland.nl"
    "medicalplaza.ua", "khmilclinic.com.ua", "blagovist.ua", "vkursi.pro", "scanbe.io", "meteo.gov.ua",
    "olx.ua", "prom.ua", "rozetka.com.ua", "hotline.ua", "petition.president.gov.ua",
    "itbox.ua", "foxtrot.com.ua", "kabanchik.ua", "work.ua", "rabota.ua", "ua.jooble.org",
    "e-schools.info", "shkola.ua", "dpa.testportal.gov.ua", "data-ua.com", "snu.edu.ua",
    "snu.edu.ua", "volyn.com.ua", "tyzhden.ua", "kse.medium.com", "kpi.stu.cn.ua",
    "ippo.kubg.edu.ua", "detector.media", "kyivoperativ.info", "economyandsociety.in.ua",
    "dspace.uzhnu.edu.ua", "er.knutd.edu.ua", "are-journal.com", "man.org.ua", "bazekon.icm.edu.pl",
    "pmc.ncbi.nlm.nih.gov", "kaf.ep.ontu.edu.ua", "astrid-online.it", "mdpi.com",
    "aeaweb.org", "es.khpi.edu.ua", "eapk.com.ua", "ir.kneu.edu.ua", "researchgate.net",
    "philarchive.org", "dlf.ua", "isg-journal.com", "ier.com.ua", "case-ukraine.com.ua",
    "gtap.agecon.purdue.edu", "onlinelibrary.wiley.com", "econpapers.repec.org",
    "www2.ifrn.edu.br", "ideas.repec.org", "cgspace.cgiar.org", "gmd.copernicus.org",
    "publications.jrc.ec.europa.eu", "opsaa.iica.int", "iopscience.iop.org", "sciencedirect.com",
    "od.vgorode.ua", "gurt.org.ua", "ostroh.info", "inneco.org", "dev.ua", "lvet.edu.ua",
    "maryanivskatg.gov.ua", "ecd.tdmu.edu.ua", "kiu.europa-uni.de", "supernet.isenberg.umass.edu",
    "papers.ssrn.com", "x.com", "universityworldnews.com", "vhptu5.vn.ua", "savvy.ua"
    "academic.oup.com", "arxiv.org", "tandfonline.com", "ageconsearch.umn.edu", "a95.ua",
    "ukr-revolution.history.org.ua", "agromaster.info", "shpolyanochka.com.ua", "repo.btu.kharkiv.ua",
    "kr-rada.gov.ua", "biotechuniv.edu.ua", "uk.wikipedia.org", "chesno.org", "open.spotify.com",
    "canactions.com", "kneu.edu.ua", "knu.ua", "hyeseonshin.com", "worldscientific.com",
    "amt.copernicus.org", "voxukraine.org", "imdb.com", "funball.org.ua", "rayrada.ck.ua",
    "new.knute.edu.ua", "en.wikipedia.org", "kiu.europa-uni.de", "savvy.ua", "laespecial.com.ar",
    "events.bank.gov.ua", "dbnl.org", "research.wur.nl", "ukma.edu.ua",
    "artsandculture.google.com", "ekmair.ukma.edu.ua", "tabs.ultimate-guitar.com", "biblioteka.cdu.edu.ua",
    "kolosok.org.ua", "zakon.rada.gov.ua", "periodicals.karazin.ua", "pharmacologyonline.silae.it",
    "molodyivchenyi.ua", "obuvna.com", "journals.uran.ua", "epc.eu", "yur-gazeta.com", "uadairy.com",
    "poleart.com", "archive.org", "lib.vsmu.by", "iovs.arvojournals.org", "marikamagazine.com",
    "ua.h-index.com", "jeeng.net", "m.ksis.eu", "beket.com.ua", "nashigroshi.org", "vakp.nlu.edu.ua",
    "laska.ua", "kniazha.ua", "citizen.in.ua", "eprints.kname.edu.ua", "istpravda.com.ua", "unba.com.ua",
    "umoloda.kiev.ua", "okhtyrka.net", "pravoslavie.poltava.ua", "shaj.sumdu.edu.ua", "grd.gov.ua",
    "journals.aps.org", "okl.kiev.ua", "fin.org.ua", "ssoar.info", "mulitvinov.cz", "sites.google.com",
    "europepmc.org", "idnes.cz", "osce.org.ua", "csecurity.kubg.edu.ua", "cordis.europa.eu", "44.ua",
    "hal.science", "indico.cern.ch", "pubs.acs.org", "meetingorganizer.copernicus.org", "jci.org",
    "books.openbookpublishers.com", "dejure.org", "hi-tech.ua", "esu.com.ua", "sid.ir", "people.rada.gov.ua",
    "laender-analysen.de", "kdpu.edu.ua", "pubs.acs.org", "polissyafc.com", "dblp.org", "bashtanskaotg.gov.ua"
]

# Legacy compatibility
blacklisted_domains = BLACKLISTED_DOMAINS

URL_STOP_WORDS: Final[list[str]] = [
    "weather", "pogoda", "snih", "dozhd", "mokryj-snih", "ozheledytsia",  # weather
    "timetable", "rozklad", "ticket", "passengers",  # transport
    "realtor", "kvartira", "orenda", "auction", "prozorro.sale",  # property/trade
    "clinic", "likar", "appointment", "reviews", "med-center",  # medicine
    "login", "signup", "register", "cart", "checkout",  # technical
    "followers", "following", "site/mathresult",  # Social networks
    "search?q=", "kved", "fo-p", "persons", "dosye",  # database
]

# Legacy compatibility
url_stop_words = URL_STOP_WORDS

LINKS_TO_REMOVE: Final[list[str]] = [
    ".pdf", ".ru",
    "https://www.bbc.com/ukrainian/news-62062756",
    "https://www.ukr.net/news/details/fotoreportazh/107095360.html",
    "https://voxukraine.org/authors/oleg-nivyevskij", "https://www.youtube.com/watch?v=ph1DKPOf9_s",
    "https://www.ifpri.org/newsletter/ifpri-insights-april-2023/",
    "https://forbes.ua/lifestyle/15-liderok-v-ukrainskiy-nautsi-spisok-forbes-13022024-19132",
    "https://www.iamo.de/en/news/news/article/iamo-bei-dem-18-eaae-kongress-food-system-transformation-in-challenging-times-in-bonn",
    "https://www.iamo.de/en/institute/staff/details/perekhozhuk/publications",
    "https://voxukraine.org/authors/kristina-kovalova",
    "https://voxukraine.org/promovchaty-chy-manipulyuvaty-yak-deputaty-poyasnyly-svoyu-pidtrymku-zakonoproyektu-12414",
    "https://voxukraine.org/authors/vladyslav-ordeha", "https://voxukraine.org/authors/ellina-yurchenko",
    "https://www.youtube.com/@%D0%94%D1%83%D1%88%D0%BA%D0%BE%D0%94%D0%BC%D0%B8%D1%82%D1%80%D0%BE",
    "https://freepolicybriefs.org/speaker_category/author/", "https://www.youtube.com/watch?v=gPHqA71BFWc",
    "https://www.youtube.com/watch?v=4h1nqwbV1v0", "https://www.youtube.com/watch?v=kt0U1xilRAI",
    "https://www.oei.fu-berlin.de/en/wirtschaft/UKRAINE/Profile/Oleg-Nivievskyi.html"
]

# Legacy compatibility
links_to_remove = LINKS_TO_REMOVE

