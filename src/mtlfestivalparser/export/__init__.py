from typing import List

from ..log_config import get_logger
from ..models import MtlEvent


class EventExporter:

    def __init__(self):
        super().__init__()
        self.logger = get_logger()

    def add_all(self, events: List[MtlEvent]) -> None:
        """Add a set of events to the export.

        :param events: The set of event to add.
        :return: None.
        """
        map(self.add, events)

    def add(self, event: MtlEvent) -> None:
        """Add a singular MtlEvent to the generated events.

        :param event: The event to add to the export.
        :return: None
        """
        pass

    def generate(self, output_path: str) -> None:
        """Create a file with the serialized events.

        :param output_path: The file to create.
        :return: None
        """
        pass
