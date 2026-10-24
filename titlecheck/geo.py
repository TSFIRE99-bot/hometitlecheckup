"""Lot geometry: size, street frontage, and which neighbors are on the left, right, behind and across the street.

Pure Python on purpose (no GIS library), so every step can be read and tested. Coordinates come from the County as
longitude / latitude. For one neighborhood the Earth is flat enough to turn them into meters with a simple scale,
which is what to_local() does.

How the neighbors are found:
1. Walk around the edge of our lot one meter at a time. At each point, step just outside the edge and see whose lot
   is there. (Stepping outside keeps a point near a corner from being counted for the lot around the corner.)
2. Edge that touches no other lot faces the street (or a park, alley...). The open side is the front of the house;
   on a corner lot with two open sides, the narrower one is the front.
3. A neighbor that shares the back edge is "behind". One that shares a side edge is "left" or "right", as seen by
   someone standing on the street, looking at the house.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

Point = tuple[float, float]
Ring = list[Point]

M_PER_DEG_LAT = 110_540
M_PER_DEG_LON_EQUATOR = 111_320
SQ_FT_PER_SQ_M = 10.7639
FT_PER_M = 3.28084
SQ_FT_PER_ACRE = 43_560

TOUCH_M = 2.0          # lots closer than this are touching (County lines don't match perfectly)
STEP_M = 1.0           # how far apart the sample points on our lot's edge are
PROBE_M = 1.5          # look this far outside our edge to see whose lot is there
PROBE_HIT_M = 1.0      # ...and accept a lot this close to that spot (County lines leave small gaps)
CORNER_M = 2.0         # shared less edge than this: the lots only meet at a corner
ACROSS_M = 60.0        # how far to look for homes across the street
OPEN_SIDE_COS = 0.7    # open edges facing within 45 deg of each other are the same side of the lot
MIN_OPEN_M = 4.0       # an open side shorter than this is a gap between County lines, not a street
SIDE_COS = 0.6         # cos(53 deg): closer to the front/back direction than this counts as front/back


@dataclass
class Neighbor:
    key: str              # whatever identifies the lot for the caller (the parcel ID)
    position: str         # "Left", "Right", "Behind", "Across the street", "Next door"
    shared_m: float       # length of the shared property line, meters
    distance_m: float     # gap between the two lots, meters (0 when touching)


@dataclass
class LotShape:
    area_sq_ft: float
    perimeter_ft: float
    frontage_ft: float | None     # length of the side facing the street, if we could tell
    front: Point | None           # unit vector pointing from the house toward the street (local meters)

    @property
    def acres(self) -> float:
        return self.area_sq_ft / SQ_FT_PER_ACRE


# ---------------------------------------------------------------- basic geometry
def to_local(rings: list[Ring], origin: Point) -> list[Ring]:
    """Longitude / latitude -> meters east / north of origin."""
    lon0, lat0 = origin
    kx = M_PER_DEG_LON_EQUATOR * math.cos(math.radians(lat0))
    return [[((x - lon0) * kx, (y - lat0) * M_PER_DEG_LAT) for x, y in ring] for ring in rings]


def signed_area(ring: Ring) -> float:
    """Shoelace formula. Positive when the points go counter-clockwise."""
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        s += x1 * y2 - x2 * y1
    return s / 2


def area(rings: list[Ring]) -> float:
    """Area of a lot. Holes are drawn in the opposite direction to the outside, so their signed areas subtract."""
    return abs(sum(signed_area(r) for r in rings))


def lot_sq_ft(rings_lonlat: list[Ring]) -> float:
    return area(to_local(rings_lonlat, rings_lonlat[0][0])) * SQ_FT_PER_SQ_M


def centroid(rings: list[Ring]) -> Point:
    """Center of mass of the biggest ring (a lot is almost always one ring)."""
    ring = max(rings, key=lambda r: abs(signed_area(r)))
    a = signed_area(ring)
    if abs(a) < 1e-9:
        xs, ys = zip(*ring)
        return sum(xs) / len(xs), sum(ys) / len(ys)
    cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        cross = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    return cx / (6 * a), cy / (6 * a)


def edges(rings: list[Ring]):
    for ring in rings:
        pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
        for p, q in zip(pts, pts[1:] + pts[:1]):
            if p != q:
                yield p, q


def perimeter(rings: list[Ring]) -> float:
    return sum(math.dist(p, q) for p, q in edges(rings))


def point_segment_distance(p: Point, a: Point, b: Point) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / length2))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def point_in_rings(p: Point, rings: list[Ring]) -> bool:
    """Ray casting: count how many edges a line going right from p crosses."""
    inside = False
    x, y = p
    for (x1, y1), (x2, y2) in edges(rings):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def distance_to(p: Point, rings: list[Ring]) -> float:
    if point_in_rings(p, rings):
        return 0.0
    return min(point_segment_distance(p, a, b) for a, b in edges(rings))


def polygon_distance(a: list[Ring], b: list[Ring]) -> float:
    """Smallest gap between two lots (0 if they overlap)."""
    if any(point_in_rings(p, b) for ring in a for p in ring) or any(point_in_rings(p, a) for ring in b for p in ring):
        return 0.0
    d1 = min(distance_to(p, b) for ring in a for p in ring)
    d2 = min(distance_to(p, a) for ring in b for p in ring)
    return min(d1, d2)


def _unit(v: Point) -> Point | None:
    n = math.hypot(*v)
    return None if n < 1e-9 else (v[0] / n, v[1] / n)


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


# ---------------------------------------------------------------- the analysis
def _walk_edge(subject: list[Ring], touching: dict[str, list[Ring]]):
    """Sample points along our lot's edge. Yields (length, outward normal, key of touching lot or None)."""
    c = centroid(subject)
    for a, b in edges(subject):
        length = math.dist(a, b)
        n = max(1, round(length / STEP_M))
        normal = _unit((b[1] - a[1], a[0] - b[0]))
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if _dot(normal, (mid[0] - c[0], mid[1] - c[1])) < 0:
            normal = (-normal[0], -normal[1])
        for i in range(n):
            t = (i + 0.5) / n
            p = (a[0] + t * (b[0] - a[0]) + PROBE_M * normal[0], a[1] + t * (b[1] - a[1]) + PROBE_M * normal[1])
            best, best_d = None, PROBE_HIT_M
            for key, rings in touching.items():
                d = distance_to(p, rings)
                if d < best_d:
                    best, best_d = key, d
            yield length / n, normal, best


def analyze(subject_lonlat: list[Ring], others_lonlat: dict[str, list[Ring]]) -> tuple[LotShape, list[Neighbor]]:
    """Measure our lot and place each nearby lot: Left, Right, Behind, Across the street."""
    origin = subject_lonlat[0][0]
    subject = to_local(subject_lonlat, origin)
    others = {k: to_local(r, origin) for k, r in others_lonlat.items() if r}
    gaps = {k: polygon_distance(subject, r) for k, r in others.items()}
    touching = {k: others[k] for k, d in gaps.items() if d < TOUCH_M}

    shared: dict[str, float] = {k: 0.0 for k in touching}
    shared_dir: dict[str, Point] = {k: (0.0, 0.0) for k in touching}
    open_sides: list[list] = []          # [direction sum, length] for each side of the lot with nobody on it
    for length, normal, key in _walk_edge(subject, touching):
        if key is None:
            side = next((sd for sd in open_sides if _dot(_unit(sd[0]), normal) > OPEN_SIDE_COS), None)
            if side is None:
                side = [(0.0, 0.0), 0.0]
                open_sides.append(side)
            side[0] = (side[0][0] + length * normal[0], side[0][1] + length * normal[1])
            side[1] += length
        else:
            shared[key] += length
            d = shared_dir[key]
            shared_dir[key] = (d[0] + length * normal[0], d[1] + length * normal[1])

    front, frontage = None, None
    if open_sides:
        # Ignore slivers where County lines don't quite meet. With more than one open side (a corner lot), the
        # front is the narrowest street side, the usual way lot frontage is defined.
        longest = max(sd[1] for sd in open_sides)
        real = [sd for sd in open_sides if sd[1] >= max(MIN_OPEN_M, 0.25 * longest)]
        side = min(real, key=lambda sd: sd[1])
        front, frontage = _unit(side[0]), side[1] * FT_PER_M

    c = centroid(subject)
    neighbors = []
    for key, rings in others.items():
        oc = centroid(rings)
        toward = _unit((oc[0] - c[0], oc[1] - c[1]))
        if key in touching:
            if shared[key] < CORNER_M:                # only the corners meet: not really a neighbor
                continue
            # which way the shared property line faces says where the neighbor is
            position = _position(_unit(shared_dir[key]), front)
            if position == "Across the street":     # touches the front: a lot that wraps around, call it next door
                position = "Next door"
            neighbors.append(Neighbor(key, position, round(shared[key], 1), 0.0))
        elif front is not None and toward is not None and gaps[key] <= ACROSS_M and _dot(toward, front) > 0.8:
            neighbors.append(Neighbor(key, "Across the street", 0.0, round(gaps[key], 1)))

    shape = LotShape(area(subject) * SQ_FT_PER_SQ_M, perimeter(subject) * FT_PER_M, frontage, front)
    order = {"Left": 0, "Right": 1, "Behind": 2, "Next door": 3, "Across the street": 4}
    neighbors.sort(key=lambda n: (order[n.position], -n.shared_m, n.distance_m))
    # keep only the closest few homes across the street
    across = [n for n in neighbors if n.position == "Across the street"][:3]
    neighbors = [n for n in neighbors if n.position != "Across the street"] + across
    return shape, neighbors


def _position(direction: Point | None, front: Point | None) -> str:
    """Where a neighbor is, as seen from the street, looking at the house."""
    if direction is None or front is None:
        return "Next door"
    along = _dot(direction, front)
    if along > SIDE_COS:
        return "Across the street"
    if along < -SIDE_COS:
        return "Behind"
    # someone on the street faces the house, so they look in the -front direction; their left is that turned 90 deg
    facing = (-front[0], -front[1])
    viewers_left = (-facing[1], facing[0])
    return "Left" if _dot(direction, viewers_left) > 0 else "Right"


def bounding_box(rings: list[Ring], pad_m: float) -> tuple[float, float, float, float]:
    """(west, south, east, north) in longitude / latitude, padded by pad_m meters on every side."""
    xs = [x for r in rings for x, _ in r]
    ys = [y for r in rings for _, y in r]
    lat = (min(ys) + max(ys)) / 2
    dlon = pad_m / (M_PER_DEG_LON_EQUATOR * math.cos(math.radians(lat)))
    dlat = pad_m / M_PER_DEG_LAT
    return min(xs) - dlon, min(ys) - dlat, max(xs) + dlon, max(ys) + dlat


def center_lonlat(rings: list[Ring]) -> Point:
    """Center of a lot, back in longitude / latitude."""
    origin = rings[0][0]
    cx, cy = centroid(to_local(rings, origin))
    kx = M_PER_DEG_LON_EQUATOR * math.cos(math.radians(origin[1]))
    return origin[0] + cx / kx, origin[1] + cy / M_PER_DEG_LAT
