import math

import pytest

from titlecheck.demo import DEMO, DEMO_NEIGHBORS
from titlecheck.geo import analyze, bounding_box, center_lonlat, lot_sq_ft, polygon_distance

LON0, LAT0 = -83.0, 40.0


def lot(x0, y0, x1, y1, turn_deg=0.0):
    """A rectangle in meters, optionally turned around the origin, as County-style (lon, lat) rings."""
    t = math.radians(turn_deg)
    kx = 111_320 * math.cos(math.radians(LAT0))
    pts = [(x0, y0), (x0, y1), (x1, y1), (x1, y0), (x0, y0)]
    turned = [(x * math.cos(t) - y * math.sin(t), x * math.sin(t) + y * math.cos(t)) for x, y in pts]
    return [[(LON0 + x / kx, LAT0 + y / 110_540) for x, y in turned]]


def street_block(turn_deg=0.0, street_side="south"):
    """Home 16 m wide and 40 m deep, a lot on each side, two behind, three across a 12 m street."""
    s = 1 if street_side == "south" else -1
    def box(x0, y0, x1, y1):
        return lot(x0, min(s * y0, s * y1), x1, max(s * y0, s * y1), turn_deg)
    home = box(-8, 6, 8, 46)
    others = {"west": box(-24, 6, -8, 46), "east": box(8, 6, 24, 46),
              "back": box(-8, 46, 8, 86), "far": box(40, 6, 56, 46),
              "across1": box(-24, -46, -8, -6), "across2": box(-8, -46, 8, -6), "across3": box(8, -46, 24, -6)}
    return home, others


def positions(home, others):
    _, found = analyze(home, others)
    return {n.key: n.position for n in found}


def test_lot_size():
    home, _ = street_block()
    assert lot_sq_ft(home) == pytest.approx(16 * 40 * 10.7639, rel=0.002)


@pytest.mark.parametrize("turn", [0, 30, 90, 200])
def test_neighbors_street_to_the_south(turn):
    home, others = street_block(turn)
    got = positions(home, others)
    # standing on the street (south) looking north at the house: west is on your left
    assert got["west"] == "Left" and got["east"] == "Right" and got["back"] == "Behind"
    assert {got["across1"], got["across2"], got["across3"]} == {"Across the street"}
    assert "far" not in got        # not touching and not across the street


def test_left_and_right_flip_when_the_street_is_north():
    home, others = street_block(street_side="north")
    got = positions(home, others)
    # standing on the street (north) looking south: east is on your left
    assert got["east"] == "Left" and got["west"] == "Right" and got["back"] == "Behind"


def test_frontage_and_shared_lines():
    home, others = street_block()
    shape, found = analyze(home, others)
    assert shape.frontage_ft == pytest.approx(16 * 3.28084, rel=0.05)
    shared = {n.key: n.shared_m for n in found}
    assert shared["west"] == pytest.approx(40, abs=1.5)
    assert shared["back"] == pytest.approx(16, abs=1.5)


def test_small_gaps_between_lots_still_count_as_touching():
    home = lot(-8, 6, 8, 46)
    got = positions(home, {"west": lot(-24, 6, -8.6, 46), "east": lot(8.4, 6, 24, 46),   # lines 0.4-0.6 m apart
                           "back": lot(-8, 46.5, 8, 86)})
    assert got == {"west": "Left", "east": "Right", "back": "Behind"}


def test_corner_lot_front_is_the_narrow_street_side():
    # streets on the south (16 m) and west (40 m) sides; the house faces the narrow south street
    shape, found = analyze(lot(-8, 6, 8, 46), {"east": lot(8, 6, 24, 46), "back": lot(-8, 46, 8, 86)})
    got = {n.key: n.position for n in found}
    assert got == {"east": "Right", "back": "Behind"}
    assert shape.frontage_ft == pytest.approx(16 * 3.28084, rel=0.1)


def test_demo_block():
    shape, found = analyze(DEMO.rings, {p.parcel_id: p.rings for p in DEMO_NEIGHBORS})
    got = {n.key: n.position for n in found}
    assert got["DEMO-1232"] == "Left" and got["DEMO-1236"] == "Right"
    assert got["DEMO-1243"] == got["DEMO-1245"] == "Behind"
    assert shape.acres == pytest.approx(0.158, abs=0.002)


def test_distance_and_box():
    a, b = lot(0, 0, 10, 10), lot(15, 0, 25, 10)
    from titlecheck.geo import to_local
    assert polygon_distance(to_local(a, a[0][0]), to_local(b, a[0][0])) == pytest.approx(5, abs=0.05)
    w, s, e, n = bounding_box(a, 70)
    lon, lat = center_lonlat(a)
    assert w < lon < e and s < lat < n
