import os

from mtlfestivalparser.export.ics import ICSEventExporter
from .log_config import get_logger
from .parser.parse import MtlOrgParser


def main():
    # TODO: integrate Typer CLI
    dir_path = os.path.dirname(os.path.realpath(__file__))
    input_dir = os.path.join(dir_path, "..", "..", "data")
    output_file = os.path.join(dir_path, "..", "..", "output.ics")
    logger = get_logger()

    exporter = ICSEventExporter()

    for data_file in os.listdir(input_dir):
        file = os.path.join(input_dir, data_file)
        logger.info(f"Checking source file {file}")
        if os.path.isfile(file):
            logger.info(f"Using source file {file}")
            for event in MtlOrgParser(file).parse():
                if not event.has_errors and event.description:
                    exporter.add(event)
    exporter.generate(output_file)


if __name__ == '__main__':
    main()
