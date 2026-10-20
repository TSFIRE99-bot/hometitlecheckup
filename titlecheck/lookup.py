"""Look up one Franklin County, Ohio property in the County Auditor's public parcel records.

Data source: Franklin County Auditor, ArcGIS REST service "ParcelFeatures/Parcel_Features", layer 0 (Tax Parcel).
Only one address is looked up at a time and nothing is saved.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

PARCEL_URL = ("https://gis.franklincountyohio.gov/hosting/rest/services/"
              "ParcelFeatures/Parcel_Features/MapServer/0/query")
AUDITOR_PARCEL_LINK = "https://audr-apps.franklincountyohio.gov/Redir/Link/Parcel/{parcel}-00"
FIELDS = ["PARCELID", "SITEADDRESS", "ZIPCD", "OWNERNME1", "OWNERNME2", "OWNERNME3",
          "SALEDATE", "CLASSDSCRP"]
TIMEOUT = 15
MAX_MATCHES = 10

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
    return {"where": _where(street, zip_code), "outFields": ",".join(FIELDS), "returnGeometry": "false",
            "orderByFields": "SITEADDRESS", "resultRecordCount": str(MAX_MATCHES), "f": "json"}


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
                              property_class=a.get("CLASSDSCRP") or "", raw=a))
    return parcels


def find_parcels(text: str, session: requests.Session | None = None) -> list[Parcel]:
    """Look up an address. Tries the exact street first, then without the street type (ST, AVE...)."""
    street, zip_code = normalize_address(text)
    http = session or requests
    tries = [street]
    words = street.split()
    if words[-1] in STREET_TYPES and len(words) > 2:
        tries.append(" ".join(words[:-1]))
    for attempt in tries:
        try:
            r = http.get(PARCEL_URL, params=build_params(attempt, zip_code), timeout=TIMEOUT)
            r.raise_for_status()
            payload = r.json()
        except requests.Timeout as e:
            raise AddressLookupError("The County's property records took too long to answer. Please try again.") from e
        except (requests.ConnectionError, requests.HTTPError) as e:
            raise AddressLookupError("Couldn't reach the County's property records right now. "
                               "You can still answer the questions using the Auditor's website.") from e
        except ValueError as e:  # response was not JSON
            raise AddressLookupError("The County's property records sent back something unexpected. Please try again.") from e
        found = parse_features(payload)
        if found:
            return found
    return []
