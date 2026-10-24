import json
from pathlib import Path

import pytest
import requests

from titlecheck.lookup import (AddressLookupError, build_params, find_in_view, find_nearby, find_parcels,
                               nearby_params, normalize_address, parcel_at, parse_features, point_params)

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "parcel_response.json").read_text())


@pytest.mark.parametrize("typed, street, zip_code", [
    ("1234 Sample Street, Columbus, OH 43200", "1234 SAMPLE ST", "43200"),
    ("373 South High St.", "373 S HIGH ST", None),
    ("55 north 4th avenue apt 2", "55 N 4TH AVE", None),
    ("  10 Main  St  ", "10 MAIN ST", None),
])
def test_normalize_address(typed, street, zip_code):
    assert normalize_address(typed) == (street, zip_code)


@pytest.mark.parametrize("bad", ["", "   ", "Main Street", "12"])
def test_normalize_rejects_non_addresses(bad):
    with pytest.raises(AddressLookupError):
        normalize_address(bad)


def test_query_cannot_be_injected():
    street, z = normalize_address("1 Main St'; DROP TABLE x --")
    where = build_params(street, z)["where"]
    assert "'" not in where.replace("LIKE '", "").replace("%'", "")
    assert "DROP TABLE X" in where  # harmless text inside the LIKE pattern, no quotes or semicolons
    assert ";" not in where


def test_parse_features():
    [p] = parse_features(FIXTURE)
    assert p.owners == ["PARKER JAMES L", "PARKER LOUISE M"]
    assert p.last_transfer.year == 1987
    assert p.is_residential
    assert p.auditor_link.endswith("/010-000000-00")


def test_parse_error_payload():
    with pytest.raises(AddressLookupError):
        parse_features({"error": {"code": 400}})


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    """Returns no match for the full street, then a match without the street type."""
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append(params.get("where"))
        return FakeResponse(self.payloads.pop(0))


def test_find_retries_without_street_type():
    s = FakeSession([{"features": []}, FIXTURE])
    found = find_parcels("1234 Sample Road", session=s)
    assert len(found) == 1
    assert s.calls == ["SITEADDRESS LIKE '1234 SAMPLE RD%'", "SITEADDRESS LIKE '1234 SAMPLE%'"]


def test_find_reports_timeout():
    class Slow:
        def get(self, *a, **k):
            raise requests.Timeout()
    with pytest.raises(AddressLookupError, match="too long"):
        find_parcels("1 Main St", session=Slow())


def test_parse_lot_outline():
    [p] = parse_features(FIXTURE)
    assert len(p.rings) == 1 and p.rings[0][0] == (-83.0, 40.0)
    assert build_params("1 MAIN ST", None)["outSR"] == "4326"


def test_find_nearby_skips_the_home_itself():
    [home] = parse_features(FIXTURE)
    neighbor = {"attributes": {**FIXTURE["features"][0]["attributes"], "PARCELID": "010-000001"},
                "geometry": {"rings": [[[-82.9998, 40.0], [-82.9998, 40.0003], [-82.9996, 40.0003],
                                        [-82.9996, 40.0], [-82.9998, 40.0]]]}}
    s = FakeSession([{"features": [FIXTURE["features"][0], neighbor]}])
    found = find_nearby(home, session=s)
    assert [p.parcel_id for p in found] == ["010-000001"]
    params = nearby_params((-83.1, 39.9, -83.0, 40.0))
    assert params["geometryType"] == "esriGeometryEnvelope" and params["inSR"] == "4326"


def test_view_and_point_queries():
    s = FakeSession([FIXTURE, FIXTURE, {"features": []}])
    assert len(find_in_view((-83.1, 39.9, -83.0, 40.0), session=s)) == 1
    assert parcel_at(-82.9999, 40.0001, session=s).parcel_id == "010-000000"
    assert parcel_at(-82.0, 40.0, session=s) is None
    p = point_params(-82.9999, 40.0001)
    assert p["geometryType"] == "esriGeometryPoint" and p["geometry"] == "-82.9999000,40.0001000"
