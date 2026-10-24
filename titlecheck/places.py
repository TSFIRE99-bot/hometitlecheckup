"""Free and official places in Franklin County that help with each step, for the "Free help near you" page.

Addresses, phone numbers and hours come from each office's own website (checked October 2026). Map points come from
the Franklin County Auditor's parcel outlines for those addresses. Check them before each release; offices move.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

GOVERNMENT_CENTER = (39.953780, -83.000208)      # 373 S. High St. (parcel 010-055568)


@dataclass
class Place:
    key: str
    name: str
    what: str               # how it helps, in plain words
    address: str
    phone: str
    hours: str
    point: tuple[float, float]
    web: str
    bring: str = ""          # what to bring

    @property
    def directions(self) -> str:
        return "https://www.google.com/maps/dir/?api=1&destination=" + quote_plus(self.address)


PLACES = [
    Place("lasco", "Legal Aid of Southeast and Central Ohio",
          "Free lawyers for families with low incomes. They help with probate, heirs' property and deeds.",
          "1108 City Park Ave., Suite 100, Columbus, OH 43206",
          "Intake (888) 246-4420 · Office (614) 221-7201",
          "Intake calls weekdays 9:30 a.m. to 1:30 p.m.; apply online any time",
          (39.939393, -82.993962), "https://www.lasco.org/apply",
          "A copy of the tax bill or deed, and any papers about the person who died."),
    Place("recorder", "Franklin County Recorder",
          "Records Transfer on Death affidavits, survivorship affidavits and deeds, and lets you search what is "
          "already recorded.",
          "373 S. High St., 18th floor, Columbus, OH 43215", "(614) 525-3930", "Weekdays; call to confirm hours",
          GOVERNMENT_CENTER, "https://www.franklincountyohio.gov/Agency-Directory/Recorder",
          "The signed, notarized form, and a check or card for the $34 fee."),
    Place("auditor", "Franklin County Auditor",
          "Homestead exemption and owner occupancy credit applications, property values and tax records.",
          "373 S. High St., 21st floor, Columbus, OH 43215", "Homestead (614) 525-3240 · Main (614) 525-4663",
          "Weekdays; you can also apply online", GOVERNMENT_CENTER,
          "https://auditor.franklincountyohio.gov/Real-Estate/Homestead",
          "Photo ID, and proof of age or disability for the homestead exemption."),
    Place("probate", "Franklin County Probate Court",
          "Handles estates after someone dies, including the shorter small-estate options. Clerks explain the steps "
          "but can't give legal advice.",
          "373 S. High St., 22nd floor, Columbus, OH 43215", "(614) 525-3894", "Monday to Friday, 8 a.m. to 5 p.m.",
          GOVERNMENT_CENTER, "https://probate.franklincountyohio.gov/",
          "Photo ID, a certified death certificate, and the original will if there is one."),
    Place("law_library", "Franklin County Law Library",
          "Free Transfer on Death forms and librarians who help you find the right form (they can't give legal "
          "advice).",
          "369 S. High St., 10th floor, Columbus, OH 43215", "(614) 525-4971", "Monday to Thursday, 8 a.m. to 5 p.m.",
          (39.954280, -83.000208), "https://fclawlib.libguides.com/TOD/transferondeathaffidavit",
          "The home's address and parcel number (it's on this app's checklist)."),
]

BY_KEY = {p.key: p for p in PLACES}
