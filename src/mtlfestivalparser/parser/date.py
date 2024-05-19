from datetime import datetime, timedelta
from typing import Optional


class DateParser:
    MONTHS_FRENCH = {
        "janvier": 1,
        "février": 2,
        "mars": 3,
        "avril": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7,
        "août": 8,
        "septembre": 9,
        "octobre": 10,
        "novembre": 11,
        "décembre": 12,

    }

    @staticmethod
    def today():
        return datetime.now().replace(hour=0, minute=0, second=0)

    @classmethod
    def get_french_months_binding(cls, month: str) -> int:
        return cls.MONTHS_FRENCH.get(month.strip().lower())

    @staticmethod
    def end_of_month(start: datetime) -> datetime:
        return datetime(start.year, start.month, 1).replace(month=(start.month + 1) % 12) - timedelta(days=1)
