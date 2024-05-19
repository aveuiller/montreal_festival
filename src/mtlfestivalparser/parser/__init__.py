from typing import List

from bs4 import BeautifulSoup

from .date import DateParser
from ..log_config import get_logger
from ..models import MtlEvent


class Parser:
    def __init__(self, source: str):
        # TODO: Take list of sources
        self.source = source
        self.logger = get_logger()

    def _fetch(self) -> List[BeautifulSoup]:
        # TODO: Download content in case of URL
        with open(self.source, 'r') as file:
            yield BeautifulSoup(file.read(), "html.parser")

    def parse(self) -> List[MtlEvent]:
        pass
