from ics import Event, Calendar

from . import EventExporter
from ..models import MtlEvent


class ICSEventExporter(EventExporter):

    def __init__(self):
        super().__init__()
        self.calendar = Calendar()

    def add(self, event: MtlEvent) -> None:
        self.logger.info(f"Adding Event {event.name}")
        ics_event = Event(
            name=event.name,
            description=f"{event.description}\n===\n{event.website}",
            begin=event.start,
            end=event.end,

        )
        ics_event.make_all_day()
        self.calendar.events.add(ics_event)

    def generate(self, output_path: str) -> None:
        with open(output_path, "w") as f:
            f.write(self.calendar.serialize())
