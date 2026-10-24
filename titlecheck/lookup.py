"""Look up one Franklin County, Ohio property in the County Auditor's public parcel records.

Data source: Franklin County Auditor, ArcGIS REST service "ParcelFeatures/Parcel_Features", layer 0 (Tax Parcel).
Only one address is looked up at a time and nothing is saved. Lot outlines come back as longitude / latitude
(outSR=4326) so they can be drawn on a web map.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

from titlecheck.geo import bounding_box

PARCEL_URL = ("https://gis.franklincountyohio.gov/hosting/rest/services/"
              "ParcelFeatures/Parcel_Features/MapServer/0/query")
AUDITOR_PARCEL_LINK = "https://audr-apps.franklincountyohio.gov/Redir/Link/Parcel/{parcel}-00"
FIELDS = ["PARCELID", "SITEADDRESS", "ZIPCD", "OWNERNME1", "OWNERNME2", "OWNERNME3",
          "SALEDATE", "CLASSDSCRP"]
TIMEOUT = 15
MAX_MATCHES = 10
MAX_NEARBY = 200
MAX_IN_VIEW = 1500       # lots drawn at once on the property map (about a 600 m by 400 m view of a neighborhood)
NEARBY_PAD_M = 70        # how far around the home to fetch other lots (about one block)

STREET_WORDS = {
    "STREET": "ST", "AVENUE": "AVE", "AV": "AVE", "ROAD": "RD", "DRIVE": "DR", "BOULEVARD": "BLVD",
    "COURT": "CT", "LANE": "LN", "PLACE": "PL", "CIRCLE": "CIR", "PARKWAY": "PKWY", "TERRACE": "TER",
    "HIGHWAY": "HWY", "TRAIL": "TRL", "SQUARE": "SQ", "PIKE": "PIKE", "WAY": "WAY",
}
DIRECTIONS = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
              "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW"}
STREET_TYPES = set(STREET_WORDS.values())
UNIT_WORDS = {"APT", "UNIT", "STE", "SUITE", "#"}


class AddressLookupError(Exception):
    """Raised with a message that can be shown to the user as-is."""


@dataclass
class Parcel:
    parcel_id: str
    address: str
    zip_code: str
    owners: list[str]
    last_transfer: datetime | None
    property_class: str
    raw: dict = field(default_factory=dict, repr=False)
    rings: list = field(default_factory=list, repr=False)   # lot outline: [[(lon, lat), ...], ...]

    @property
    def auditor_link(self) -> str:
        return AUDITOR_PARCEL_LINK.format(parcel=self.parcel_id)

    @property
    def years_since_transfer(self) -> int | None:
        if self.last_transfer is None:
            return None
        return int((datetime.now(timezone.utc) - self.last_transfer).days // 365.25)

    @property
    def is_residential(self) -> bool:
        c = self.property_class.upper()
        return any(w in c for w in ("DWELLING", "SINGLE FAMILY", "TWO FAMILY", "THREE FAMILY", "CONDOMINIUM"))


def normalize_address(text: str) -> tuple[str, str | None]:
    """'123 North High Street, Columbus, OH 43215' -> ('123 N HIGH ST', '43215').

    Returns the street part in the County's format plus the ZIP code if one was typed.
    """
    if not text or not text.strip():
        raise AddressLookupError("Please type a street address, like 123 Main St.")
    zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\s*$", text.strip())
    zip_code = zip_match.group(1) if zip_match else None
    street = text.split(",")[0].upper()
    street = re.sub(r"[^A-Z0-9 #]", " ", street)
    words = street.split()
    out = []
    for w in words:
        if w in UNIT_WORDS:          # stop at apartment / unit numbers
            break
        out.append(DIRECTIONS.get(w, STREET_WORDS.get(w, w)))
    if zip_code and out and out[-1] == zip_code:
        out = out[:-1]
    if len(out) < 2 or not out[0][0].isdigit():
        raise AddressLookupError("Start with the house number, then the street name, like 123 Main St.")
    return " ".join(out), zip_code


def _where(street: str, zip_code: str | None) -> str:
    safe = re.sub(r"[^A-Z0-9 ]", "", street)  # only letters, numbers, spaces reach the query
    clause = f"SITEADDRESS LIKE '{safe}%'"
    if zip_code:
        clause += f" AND ZIPCD = '{zip_code}'"
    return clause


def build_params(street: str, zip_code: str | None) -> dict:
    return {"where": _where(street, zip_code), "outFields": ",".join(FIELDS), "returnGeometry": "true",
            "outSR": "4326", "orderByFields": "SITEADDRESS", "resultRecordCount": str(MAX_MATCHES), "f": "json"}


def nearby_params(box: tuple[float, float, float, float], limit: int = MAX_NEARBY) -> dict:
    """Every lot that overlaps a box (west, south, east, north) in longitude / latitude."""
    return {"geometry": ",".join(f"{v:.7f}" for v in box), "geometryType": "esriGeometryEnvelope", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects", "where": "1=1", "outFields": ",".join(FIELDS),
            "returnGeometry": "true", "outSR": "4326", "resultRecordCount": str(limit), "f": "json"}


def point_params(lon: float, lat: float) -> dict:
    """The lot under one point on the map."""
    return {"geometry": f"{lon:.7f},{lat:.7f}", "geometryType": "esriGeometryPoint", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects", "where": "1=1", "outFields": ",".join(FIELDS),
            "returnGeometry": "true", "outSR": "4326", "f": "json"}


def _rings(geometry: dict | None) -> list:
    if not geometry:
        return []
    return [[(float(x), float(y)) for x, y, *_ in ring] for ring in geometry.get("rings", []) if len(ring) >= 3]


def parse_features(payload: dict) -> list[Parcel]:
    if "error" in payload:
        raise AddressLookupError("The County's property records answered with an error. Please try again in a minute.")
    parcels = []
    for feat in payload.get("features", []):
        a = feat.get("attributes", {})
        owners = [a.get(k).strip() for k in ("OWNERNME1", "OWNERNME2", "OWNERNME3") if a.get(k) and a.get(k).strip()]
        sale = a.get("SALEDATE")
        last = datetime.fromtimestamp(sale / 1000, tz=timezone.utc) if isinstance(sale, (int, float)) and sale > 0 else None
        parcels.append(Parcel(parcel_id=a.get("PARCELID", ""), address=a.get("SITEADDRESS") or "",
                              zip_code=a.get("ZIPCD") or "", owners=owners, last_transfer=last,
                              property_class=a.get("CLASSDSCRP") or "", raw=a, rings=_rings(feat.get("geometry"))))
    return parcels


def _query(params: dict, session) -> list[Parcel]:
    http = session or requests
    try:
        r = http.get(PARCEL_URL, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        payload = r.json()
    except requests.Timeout as e:
        raise AddressLookupError("The County's property records took too long to answer. Please try again.") from e
    except (requests.ConnectionError, requests.HTTPError) as e:
        raise AddressLookupError("Couldn't reach the County's property records right now. "
                                 "You can still answer the questions using the Auditor's website.") from e
    except ValueError as e:  # response was not JSON
        raise AddressLookupError("The County's property records sent back something unexpected. Please try again.") from e
    return parse_features(payload)


def find_parcels(text: str, session: requests.Session | None = None) -> list[Parcel]:
    """Look up an address. Tries the exact street first, then without the street type (ST, AVE...)."""
    street, zip_code = normalize_address(text)
    tries = [street]
    words = street.split()
    if words[-1] in STREET_TYPES and len(words) > 2:
        tries.append(" ".join(words[:-1]))
    for attempt in tries:
        found = _query(build_params(attempt, zip_code), session)
        if found:
            return found
    return []


def find_nearby(parcel: Parcel, session: requests.Session | None = None) -> list[Parcel]:
    """The lots around a home (about one block), not counting the home itself. Needs the home's outline."""
    if not parcel.rings:
        return []
    found = _query(nearby_params(bounding_box(parcel.rings, NEARBY_PAD_M)), session)
    return [p for p in found if p.parcel_id != parcel.parcel_id and p.rings]


def find_in_view(box: tuple[float, float, float, float], session: requests.Session | None = None) -> list[Parcel]:
    """Every lot inside the part of the map on screen (west, south, east, north), for drawing property lines."""
    return [p for p in _query(nearby_params(box, MAX_IN_VIEW), session) if p.rings]


def parcel_at(lon: float, lat: float, session: requests.Session | None = None) -> Parcel | None:
    """The lot someone clicked on, or None if the point isn't on a lot (a street, a river...)."""
    found = [p for p in _query(point_params(lon, lat), session) if p.rings]
    return found[0] if found else None
