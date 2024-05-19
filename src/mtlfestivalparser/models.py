import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class MtlEvent:
    name: str
    description: str
    start: datetime
    end: datetime
    website: str
    errors: List[str] = dataclasses.field(default_factory=list)

    @property
    def has_errors(self):
        return any(self.errors)
