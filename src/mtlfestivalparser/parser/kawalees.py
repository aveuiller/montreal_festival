from datetime import datetime
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup, Tag
from mtlfestivalparser.models import MtlEvent
from mtlfestivalparser.parser import Parser


class KawaleesParser(Parser):
    """Parser for the Kawalees events calendar page (SimpleCalendar/SimCal plugin)."""

    SOURCE_URL = "https://kawalees.ca/events-calendar/"
    CACHE_FILE = "kawalees_events.html"

    # SimCal renders dates as ISO 8601 in the `content` attribute of
    # itemprop="startDate" / itemprop="endDate" spans.
    # e.g. content="2026-05-21T20:00:00-04:00"
    WEBSITE = SOURCE_URL

    def __init__(self, cache: Path | None = None):
        super().__init__(
            source=self.SOURCE_URL,
            filename=self.CACHE_FILE,
            cache=cache,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, force_download: bool = False) -> List[MtlEvent]:
        events: List[MtlEvent] = []
        for soup in self._fetch(force_download):
            events.extend(self._parse_all_events(soup))
        return events

    # ------------------------------------------------------------------
    # Core parsing
    # ------------------------------------------------------------------

    def _parse_all_events(self, soup: BeautifulSoup) -> List[MtlEvent]:
        """
        SimCal structure:
            <dl class="simcal-events-list-container">
                <dt class="simcal-day-label">…date label…</dt>
                <dd class="simcal-day-has-events …">
                    <ul class="simcal-events">
                        <li class="simcal-event …">
                            <div class="simcal-event-details">…</div>
                        </li>
                    </ul>
                </dd>
            </dl>
        """
        events: List[MtlEvent] = []

        dl = soup.find("dl", class_="simcal-events-list-container")
        if not dl:
            self.logger.warning("No SimCal event list found on page.")
            return events

        for li in dl.select("li.simcal-event"):
            event = self._parse_event_li(li)
            if event:
                events.append(event)

        return events

    def _parse_event_li(self, li: Tag) -> MtlEvent | None:
        errors: List[str] = []
        details = li.find("div", class_="simcal-event-details")
        if not details:
            return None

        # ---- name ----
        title_span = details.find("span", class_="simcal-event-title")
        name = title_span.get_text(strip=True) if title_span else ""
        if not name:
            errors.append("Missing event title")

        # ---- start datetime ----
        # The start date span carries itemprop="startDate" and a precise
        # ISO timestamp in its `content` attribute.
        start = self._parse_iso_from_itemprop(details, "startDate", errors)

        # ---- end datetime ----
        # The end time span carries itemprop="endDate".
        end = self._parse_iso_from_itemprop(details, "endDate", errors)

        # Fall back: if end is missing, use end-of-day of the start date
        if end == datetime.min and start != datetime.min:
            end = start.replace(hour=23, minute=59, second=59)
            errors.append("End date missing; defaulted to end of start day")

        # ---- description ----
        desc_div = details.find("div", class_="simcal-event-description")
        description = desc_div.get_text(" ", strip=True) if desc_div else ""

        # ---- website ----
        # SimCal provides a Google Calendar link; we use the venue website
        # as the canonical URL since there's no per-event page.
        gcal_link = details.find("a", href=lambda h: h and "google.com/calendar/event" in h)
        website = gcal_link["href"] if gcal_link else self.WEBSITE

        return MtlEvent(
            source="kawalees",
            name=name,
            description=description,
            start=start,
            end=end,
            website=website,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Date helpers
    # ------------------------------------------------------------------

    def _parse_iso_from_itemprop(
            self,
            details: Tag,
            itemprop: str,
            errors: List[str],
    ) -> datetime:
        """
        Find the span with the given itemprop and parse its `content` attribute
        as an ISO 8601 datetime.

        SimCal renders two spans with itemprop="startDate":
          - one for the start date (class simcal-event-start-date)
          - one for the start time (class simcal-event-start-time)
        And one span with itemprop="endDate" for the end time.

        The `content` attribute on any of these carries the full ISO timestamp,
        so we just grab the first matching span that has a non-empty `content`.
        """
        for span in details.find_all("span", itemprop=itemprop):
            content = span.get("content", "").strip()
            if content:
                dt = self._parse_iso(content, errors)
                if dt != datetime.min:
                    return dt

        errors.append(f"Missing or unparseable {itemprop} timestamp")
        return datetime.min

    @staticmethod
    def _parse_iso(iso_str: str, errors: List[str]) -> datetime:
        """
        Parse an ISO 8601 datetime string like '2026-05-21T20:00:00-04:00'.
        Returns a timezone-aware datetime, or datetime.min on failure.
        """
        try:
            # Python 3.7+ fromisoformat handles offset-aware strings
            return datetime.fromisoformat(iso_str)
        except ValueError:
            # Fallback: strip trailing 'Z' and retry
            try:
                return datetime.fromisoformat(iso_str.rstrip("Z"))
            except ValueError:
                errors.append(f"Could not parse ISO datetime: {iso_str!r}")
                return datetime.min
