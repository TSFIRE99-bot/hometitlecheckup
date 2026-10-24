"""A made-up home and a made-up block around it, so anyone can try the app without looking up a real family.

The lots are drawn in meters on a grid and turned into longitude / latitude the same way the County's data comes in.
The demo map is shown without satellite or street tiles, so it never points at a real house.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from titlecheck.lookup import Parcel

ORIGIN = (-82.95, 39.95)     # only used to turn meters into coordinates; no map tiles are shown for the demo
LOT_DEPTH = 40
STREET_HALF_WIDTH = 6

# (house number, owner(s), x from, x to): north side of Sample St, house fronts face south
NORTH = [(1230, ["GARCIA ROSA"], -40, -24), (1232, ["NGUYEN THANH", "NGUYEN MAI"], -24, -8),
         (1234, ["PARKER JAMES L", "PARKER LOUISE M"], -8, 8),
         (1236, ["WASHINGTON DORIS J"], 8, 24), (1238, ["OSEI KWAME"], 24, 40)]
# across the street (south side)
SOUTH = [(1231, ["MILLER TOM"], -40, -24), (1233, ["ABDI HODAN"], -24, -8), (1235, ["CHEN WEI"], -8, 8),
         (1237, ["JOHNSON LAMAR"], 8, 24), (1239, ["ROSSI ANNA"], 24, 40)]
# behind: lots on Elm St, whose fronts face north
BEHIND = [(1241, ["BROWN KAREN"], -40, -20), (1243, ["SINGH ARJUN"], -20, 0), (1245, ["LOPEZ MARIA"], 0, 20),
          (1247, ["KOWALSKI PETER"], 20, 40)]


def _lonlat(x: float, y: float) -> tuple[float, float]:
    lon0, lat0 = ORIGIN
    return lon0 + x / (111_320 * math.cos(math.radians(lat0))), lat0 + y / 110_540


def _box(x0: float, y0: float, x1: float, y1: float) -> list:
    # clockwise, closed, like the County's outer rings
    return [[_lonlat(x0, y0), _lonlat(x0, y1), _lonlat(x1, y1), _lonlat(x1, y0), _lonlat(x0, y0)]]


def _parcel(number: int, street: str, owners: list[str], rings: list, year: int) -> Parcel:
    return Parcel(parcel_id=f"DEMO-{number}", address=f"{number} {street} (demo)", zip_code="43200", owners=owners,
                  last_transfer=datetime(year, 6, 1, tzinfo=timezone.utc), property_class="SINGLE FAMILY DWELLING",
                  rings=rings)


def _block() -> tuple[Parcel, list[Parcel]]:
    top = STREET_HALF_WIDTH + LOT_DEPTH
    home, others = None, []
    for i, (n, owners, x0, x1) in enumerate(NORTH):
        p = _parcel(n, "SAMPLE ST", owners, _box(x0, STREET_HALF_WIDTH, x1, top), 1980 + 7 * i)
        if n == 1234:
            home = p
        else:
            others.append(p)
    for i, (n, owners, x0, x1) in enumerate(SOUTH):
        others.append(_parcel(n, "SAMPLE ST", owners, _box(x0, -top, x1, -STREET_HALF_WIDTH), 1990 + 5 * i))
    for i, (n, owners, x0, x1) in enumerate(BEHIND):
        others.append(_parcel(n, "ELM ST", owners, _box(x0, top, x1, top + LOT_DEPTH), 1995 + 4 * i))
    home.address = "1234 SAMPLE ST (demo home, not real)"
    home.parcel_id = "DEMO"
    home.last_transfer = datetime(1987, 6, 1, tzinfo=timezone.utc)
    return home, others


DEMO, DEMO_NEIGHBORS = _block()
