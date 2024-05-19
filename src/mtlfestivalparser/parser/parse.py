import re
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

from . import Parser
from .date import DateParser
from ..models import MtlEvent


class MtlOrgParser(Parser):
    """
    <p><a href="https://www.mtl.org/fr/quoi-faire/festivals-et-evenements/festival-eureka-ile-du-savoir"><strong>Festival Eurêka!</strong></a><strong> (du 24 au 26 mai 2024)</strong></p>
    <p>De retour pour une 17<sup>e</sup> édition, le plus grand festival scientifique du Québec prendra d’assaut le parc Jean-Drapeau et l’emblématique Biosphère pour y présenter plus d’une centaine d’activités, d’ateliers et de démonstrations à caractère scientifique qui plairont à toute la famille. Le <a href="https://festivaleureka.ca/eureka-virtuel/">volet virtuel</a> (et gratuit) du festival Eurêka! demeure d’ailleurs accessible à longueur d’année sur son site web!</p>
    """

    DATE_REGEX = (r"\((?:du|de|le)?(?P<start_day> ?\d+)?(?:er)?(?P<start_month> \w+)? "
                  r"(?:au|à|et)(?P<end_day> \d+)?(?:er)? (?P<end_month>\w+)(?P<year> \d+)?\)")
    EACH_YEAR_REGEX = r"\(chaque année (?:d’|en |de )(?P<start_month>\w+)(?: à)?(?P<end_month> \w+)?\)"
    SPECIFIC_DAY_REGEX = r"\((le )?(?P<day>\d+)(?:er)?(?P<month> \w+)(?P<year> \d+)?\)"

    def _sanitize(self, text: str) -> str:
        return text.strip().replace("\xa0", " ")

    def parse(self) -> List[MtlEvent]:
        for content in self._fetch():
            # Event description uses 2 paragraphs, one after the other
            event = {}
            for paragraph in content.find_all('p'):
                if not event:
                    if paragraph.find_next('a') is None:
                        self.logger.info(f"Skipping paragraph without event: {paragraph}")
                        continue
                    self.logger.trace(f"Parsing: {paragraph}")
                    name_tag = paragraph.find_next('strong')
                    time = name_tag.find_next('strong').getText()
                    start, end, error = self._extract_dates(self._sanitize(time))
                    event = {
                        "name": self._sanitize(name_tag.getText()),
                        "website": paragraph.find_next('a').get('href'),
                        "start": start,
                        "end": end,
                    }
                    if error:
                        event.setdefault("errors", []).append(error)
                # Second line
                else:
                    event["description"] = self._sanitize(paragraph.getText())
                    yield MtlEvent(**event)
                    event = {}

    def _extract_dates(self, time) -> Tuple[datetime, datetime, Optional[str]]:
        """
        Integrated
            (du 5 au 7 septembre 2024)
            (du 18 juillet au 4 août 2024)
            (de juin à octobre)
            (le 30 août et 1er septembre 2024)
            (chaque année en août)
            (chaque année d’août à septembre)
            (chaque année de juin à août)
            (le 4 août 2024)
            (30 mai 2024)
        Not handled:
            (en cours)
            (fin mai)
        :param time:
        :return:
        """
        start = datetime.now().replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        error = None

        self.logger.trace(f"Parsing time: {time}")

        if match := re.match(self.DATE_REGEX, time):
            groups = match.groupdict()
            self.logger.trace(f"Parsed time: {groups}")
            year: int = int(groups.get("year") or datetime.now().year)
            start = datetime(year,
                             DateParser.get_french_months_binding(groups.get("start_month") or groups.get("end_month")),
                             int(groups.get("start_day") or 1))
            end = datetime(year,
                           DateParser.get_french_months_binding(groups.get("end_month")),
                           int(groups.get("end_day") or 1))
            if "end_day" not in groups:
                end = DateParser.end_of_month(end)
        elif match := re.match(self.EACH_YEAR_REGEX, time):
            start = datetime(datetime.now().year,
                             DateParser.get_french_months_binding(match.group("start_month")),
                             1)
            if match.group("end_month") is not None:
                end = DateParser.end_of_month(datetime(start.year,
                                                       DateParser.get_french_months_binding(match.group("end_month")),
                                                       1))
            else:
                end = DateParser.end_of_month(start)
        elif match := re.match(self.SPECIFIC_DAY_REGEX, time):
            start = datetime(datetime.now().year,
                             DateParser.get_french_months_binding(match.group("month")),
                             int(match.group("day")))
            end = start
        else:
            error = f"Unable to extract dates from string {time}"
            self.logger.warning(error)

        return start, end, error
