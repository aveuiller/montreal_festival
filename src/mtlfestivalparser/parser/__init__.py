from pathlib import Path
from typing import List, Any, Generator

import requests
from bs4 import BeautifulSoup
from ..log_config import get_logger
from ..models import MtlEvent


class Parser:
    def __init__(self, source: str, filename: str, cache: Path | None = None):
        self.source = source
        self.filename = filename
        self.cache = cache or Path("./mtlparserdata")
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0"
        }
        self.logger = get_logger()

    def _fetch(self, force_download: bool = False) -> Generator[BeautifulSoup, Any, None]:
        if not (self.cache / self.filename).exists() or force_download:
            self._download()
        with open(self.cache / self.filename, 'r') as file:
            yield BeautifulSoup(file.read(), "html.parser")

    def parse(self) -> List[MtlEvent]:
        pass

    def _download(self):
        self.logger.info(f"Downloading file for {self.__class__.__name__} - {self.filename} in cache {self.cache}")
        self.cache.mkdir(exist_ok=True)
        response = requests.get(self.source, headers=self.headers)
        response.raise_for_status()
        with open(self.cache / self.filename, "w") as file:
            file.write(response.text)
