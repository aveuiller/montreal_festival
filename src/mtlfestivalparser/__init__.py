import enum
import os
from pathlib import Path

import typer
from mtlfestivalparser.export.ics import ICSEventExporter
from mtlfestivalparser.parser.kawalees import KawaleesParser
from .log_config import get_logger
from .parser.mtl_org import MtlOrgParser


class AvailableSources(enum.Enum):
    MTL_ORG = "mtl.org"
    KAWALEES = "kawalees"


AVAILABLE_PARSERS = {
    AvailableSources.MTL_ORG: MtlOrgParser,
    AvailableSources.KAWALEES: KawaleesParser
}


def parse(cache_dir: Path | None = None, output_file: Path | None = None,
          sources: list[AvailableSources] | None = None, force_download: bool = False):
    dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
    if not output_file:
        output_file = dir_path.parent.parent / "output.ics"
    if not sources:
        sources = [ap for ap in AvailableSources]

    logger = get_logger()
    exporter = ICSEventExporter()

    logger.info(f"Parsing events from {[s.name for s in sources]} towards {output_file}")
    for source in sources:
        parser_class = AVAILABLE_PARSERS.get(source)
        if parser_class is None:
            logger.error(f"Unable to find parser bound to source {source}, skipping.")
        logger.info(f"Using parser {source.name} - {parser_class}")
        for event in parser_class(cache_dir).parse(force_download):
            if not event.has_errors and event.description:
                exporter.add(event)

    exporter.generate(output_file)


def main():
    typer.run(parse)


if __name__ == '__main__':
    main()
