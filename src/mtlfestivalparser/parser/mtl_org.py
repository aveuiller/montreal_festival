import re
from datetime import datetime
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup, Tag
from mtlfestivalparser.models import MtlEvent
from mtlfestivalparser.parser import Parser


class MtlOrgParser(Parser):
    """Parser for the mtl.org summer festival guide article."""

    SOURCE_URL = "https://www.mtl.org/fr/experience/guide-des-festivals-dete-montreal"
    CACHE_FILE = "mtl_summer_festivals.html"

    FRENCH_MONTHS = {
        "janvier": 1, "février": 2, "mars": 3, "avril": 4,
        "mai": 5, "juin": 6, "juillet": 7, "août": 8,
        "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
    }

    # Patterns for date ranges and single dates
    # "du 17 avril au 9 mai 2026"
    _RE_RANGE = re.compile(
        r"du\s+(\d{1,2})\s*(?:er)?\s+(\w+)?\s*au\s+(\d{1,2})\s*(?:er)?\s+(\w+)\s+(\d{4})",
        re.IGNORECASE,
    )
    # "du 1er au 3 mai 2026"  (same-month range, first month omitted)
    _RE_RANGE_SAME_MONTH = re.compile(
        r"du\s+(\d{1,2})\s*(?:er)?\s+au\s+(\d{1,2})\s*(?:er)?\s+(\w+)\s+(\d{4})",
        re.IGNORECASE,
    )
    # "le 2 août 2026"
    _RE_SINGLE = re.compile(
        r"le\s+(\d{1,2})\s*(?:er)?\s+(\w+)\s+(\d{4})",
        re.IGNORECASE,
    )
    # "les 12 et 13 septembre 2026"
    _RE_TWO_DAYS = re.compile(
        r"les\s+(\d{1,2})\s+et\s+(\d{1,2})\s+(\w+)\s+(\d{4})",
        re.IGNORECASE,
    )

    def __init__(self, cache: Path | None = None):
        super().__init__(
            source=self.SOURCE_URL,
            filename=self.CACHE_FILE,
            cache=cache,
        )

    def parse(self, force_download: bool = False) -> List[MtlEvent]:
        events: List[MtlEvent] = []
        for soup in self._fetch(force_download):
            events.extend(self._parse_all_events(soup))
        return events

    def _parse_all_events(self, soup: BeautifulSoup) -> List[MtlEvent]:
        """
        The page structure inside .wysiwyg blocks is:
            <p><a class="btn-primary" href="…">EVENT NAME</a></p>
            <ul>
              <li>…Quand…</li>
              <li>…Où…</li>
              <li>…Quoi…</li>
            </ul>
        We walk every btn-primary anchor and grab its sibling <ul>.
        """
        events: List[MtlEvent] = []

        for anchor in soup.select("a.btn-primary"):
            # Skip anchors not inside a wysiwyg block (nav, related, etc.)
            if not anchor.find_parent(class_="wysiwyg"):
                continue

            name = anchor.get_text(strip=True)
            website = anchor.get("href", "")

            # The <ul> we want is the next sibling <ul> after the <p> that
            # wraps the anchor.
            parent_p = anchor.find_parent("p")
            if parent_p is None:
                continue

            ul = self._next_sibling_ul(parent_p)
            if ul is None:
                self.logger.warning(f"No <ul> found after btn-primary for '{name}'")
                continue

            event = self._parse_event_block(name, website, ul)
            events.append(event)

        return events

    def _next_sibling_ul(self, tag: Tag) -> Tag | None:
        """Return the first <ul> among the next siblings of tag."""
        sibling = tag.next_sibling
        while sibling:
            if isinstance(sibling, Tag):
                if sibling.name == "ul":
                    return sibling
                # Stop if we hit another <p> with a btn-primary (next event)
                if sibling.name == "p" and sibling.find("a", class_="btn-primary"):
                    return None
            sibling = sibling.next_sibling
        return None

    def _parse_event_block(self, name: str, website: str, ul: Tag) -> MtlEvent:
        """Parse Quand / Où / Quoi from the <ul> block."""
        errors: List[str] = []
        labelled: dict[str, str] = {}
        desc_text = ""

        for li in ul.find_all("li", recursive=False):
            text = li.get_text(" ", strip=True).replace("\xa0", " ")
            strong = li.find("strong")
            if strong:
                label = strong.get_text(strip=True).rstrip(":").strip()
                # Strip "Label : " prefix from the full text
                value = re.sub(r"^.*?:\s*", "", text, count=1).strip()
                labelled[label] = value
            else:
                # Unlabelled li (some events use plain text without bold)
                key = self._guess_label(text)
                if key:
                    value = re.sub(r"^(?:Quand|Où|Quoi)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
                    labelled[key] = value
                else:
                    desc_text = text  # fallback

        # ---- date ----
        raw_date = labelled.get("Quand", "")
        start, end = self._parse_date_range(raw_date, errors)

        # ---- description ----
        description = labelled.get("Quoi", desc_text)
        if not description:
            errors.append("Missing 'Quoi' field")

        return MtlEvent(
            source="mtl.org",
            name=name,
            description=description,
            start=start,
            end=end,
            website=website,
            errors=errors,
        )

    def _parse_date_range(
            self, raw: str, errors: List[str]
    ) -> tuple[datetime, datetime]:
        default = datetime.min
        clean = raw.replace("\xa0", " ").strip()

        # "les 12 et 13 septembre 2026"
        m = self._RE_TWO_DAYS.search(clean)
        if m:
            d1, d2, month_str, year = m.groups()
            dt = self._make_dt(int(d1), month_str, int(year), errors)
            dt2 = self._make_dt(int(d2), month_str, int(year), errors)
            if dt and dt2:
                return dt.replace(hour=0), dt2.replace(hour=23, minute=59, second=59)

        # "du 17 avril au 9 mai 2026"  (cross-month)
        m = self._RE_RANGE.search(clean)
        if m:
            d1, m1_str, d2, m2_str, year = m.groups()
            month1 = m1_str or m2_str  # first month may be omitted
            dt_start = self._make_dt(int(d1), month1, int(year), errors)
            dt_end = self._make_dt(int(d2), m2_str, int(year), errors)
            if dt_start and dt_end:
                # Handle year rollover (e.g. "du 28 décembre au 2 janvier 2027")
                if dt_end < dt_start:
                    dt_end = dt_end.replace(year=dt_end.year + 1)
                return dt_start.replace(hour=0), dt_end.replace(hour=23, minute=59, second=59)

        # "du 1er au 3 mai 2026"  (same-month)
        m = self._RE_RANGE_SAME_MONTH.search(clean)
        if m:
            d1, d2, month_str, year = m.groups()
            dt_start = self._make_dt(int(d1), month_str, int(year), errors)
            dt_end = self._make_dt(int(d2), month_str, int(year), errors)
            if dt_start and dt_end:
                return dt_start.replace(hour=0), dt_end.replace(hour=23, minute=59, second=59)

        # "le 2 août 2026"
        m = self._RE_SINGLE.search(clean)
        if m:
            day, month_str, year = m.groups()
            dt = self._make_dt(int(day), month_str, int(year), errors)
            if dt:
                return dt.replace(hour=0), dt.replace(hour=23, minute=59, second=59)

        if clean:
            errors.append(f"Could not parse date: {clean!r}")
        else:
            errors.append("Missing 'Quand' field")

        return default, default

    def _make_dt(
            self, day: int, month_str: str, year: int, errors: List[str]
    ) -> datetime | None:
        month = self.FRENCH_MONTHS.get(month_str.lower().strip())
        if not month:
            errors.append(f"Unknown month: {month_str!r}")
            return None
        try:
            return datetime(year, month, day)
        except ValueError as exc:
            errors.append(f"Invalid date {day}/{month}/{year}: {exc}")
            return None

    def _guess_label(self, text: str) -> str | None:
        """Detect unlabelled Quand/Où/Quoi from plain text prefix."""
        t = text.lower()
        if t.startswith("quand"):
            return "Quand"
        if t.startswith("où"):
            return "Où"
        if t.startswith("quoi"):
            return "Quoi"
        return None
