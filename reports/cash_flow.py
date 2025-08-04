import logging
from datetime import datetime
from typing import Generator, List, Tuple


def generate_timeline(
    items,
    end: datetime,
) -> Generator[Tuple[str, str, List[Tuple[datetime, Tuple[float, str]]]], None, None]:
    for v in items.values():
        for asset in v:
            tl = asset.get_timeline(end)
            if len(tl) == 0:
                continue
            logging.debug(f"Timeline for {asset.identifier}: {tl}")
            yield (asset.country, asset.identifier, tl)
