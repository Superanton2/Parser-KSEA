from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True)
class SearchConfig:
    """Configuration for Google Custom Search API."""
    api_key: str = "API KEY FROM https://console.cloud.google.com/apis/credentials"
    search_engine_id: str = "SEARCH ENGINE ID FROM https://cse.google.com/"
    max_results: int = 100
    sort_by_date: bool = True
    region: str = "ua"
    # Optional absolute date range for filtering Google results (CSE 'sort' param)
    # Acceptable formats: "YYYY-MM-DD" or "YYYYMMDD". Leave as None to ignore.
    date_from: str | None = None
    date_to: str | None = None


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

# Default model for local/remote LLM usage. Change to your preferred model.
LLM_MODEL: Final[str] = "gemma:2b"

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
