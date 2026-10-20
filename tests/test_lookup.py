import json
from pathlib import Path

import pytest
import requests

from titlecheck.lookup import AddressLookupError, build_params, find_parcels, normalize_address, parse_features

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
        self.calls.append(params["where"])
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
