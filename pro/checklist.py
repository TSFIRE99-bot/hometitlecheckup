"""The default intake checklist for an inherited-home matter in Franklin County, and the missing-item rules.

This is a starting template, not legal guidance about what a matter requires. Until an attorney at the firm approves
it, every screen and packet labels the checklist "Draft: awaiting professional approval". Firms can mark items as not
needed for a particular case.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ItemTemplate:
    key: str
    label: str
    kind: str            # document or information
    required: bool
    accepts: tuple[str, ...] = ()   # document types (pro/extract.DOC_TYPES) that satisfy a document item
    family_can_provide: bool = True


DEFAULT = (
    ItemTemplate("death_certificate", "Certified death certificate", "document", True, ("death_certificate",)),
    ItemTemplate("deed", "Most recent recorded deed for the home", "document", True, ("deed", "tod_affidavit")),
    ItemTemplate("tax_bill", "Most recent property tax bill", "document", True, ("tax_bill",)),
    ItemTemplate("will", "Will, if there is one", "document", False, ("will",)),
    ItemTemplate("mortgage", "Mortgage statement, if there is a loan", "document", False, ("mortgage_statement",)),
    ItemTemplate("family_tree", "Names and relationships of surviving family members", "information", True),
    ItemTemplate("contact", "Best contact person and how to reach them", "information", True),
    ItemTemplate("county_record", "Franklin County Auditor record (retrieved by staff)", "information", True,
                 family_can_provide=False),
)

BY_KEY = {item.key: item for item in DEFAULT}

DONE = {"received", "approved", "not_needed"}

STATUS_LABELS = {"missing": "Missing", "requested": "Requested", "received": "Received, needs review",
                 "approved": "Approved", "not_needed": "Not needed for this case"}


def item_for_document(doc_type: str) -> str | None:
    for item in DEFAULT:
        if doc_type in item.accepts:
            return item.key
    return None


def outstanding(item_rows) -> list:
    """Required items not yet received, approved or marked not needed."""
    return [i for i in item_rows if i.required and i.status not in DONE]
