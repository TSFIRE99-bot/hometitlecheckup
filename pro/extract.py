"""Reads uploaded documents and proposes fields for staff review.

Pipeline: plain text from text-based PDFs (pypdf), then an extractor that sorts the document into a type and proposes
fields. Every proposed field keeps the page and the exact line it came from. Nothing here decides anything: proposals
start as "awaiting review", and staff approve or correct them.

The default extractor is rule-based and needs no network or credentials. It doubles as the mock mode for the demo and
the tests. A hosted AI model can be added later as another class with the same two methods, chosen by PRO_EXTRACTOR,
once (1) an evaluation on authorized, de-identified documents shows it beats the rules, and (2) the firm has approved
the provider's data-use and retention terms. Its key would stay on the server, with per-case page, token and spending
limits recorded in the usage table. Scanned PDFs and photos need OCR, which is not set up; they are marked unreadable
so staff can enter the fields by hand.

Document text is untrusted data. The extractor only fills a fixed set of field keys, never sends messages or changes
settings, and flags text that looks like instructions aimed at software so staff can see it.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass

FIELD_LABELS = {
    "decedent_name": "Name of the person who died",
    "date_of_death": "Date of death",
    "property_address": "Property address",
    "parcel_id": "Parcel number",
    "deed_type": "Deed type",
    "deed_grantees": "Owners named on the deed",
    "recording_date": "Deed recording date",
    "instrument_number": "Recorder instrument number",
    "tod_beneficiaries": "Beneficiaries named on a Transfer on Death affidavit",
    "will_date": "Date of the will",
    "will_executor": "Executor named in the will",
    "tax_owner": "Owner listed on the tax bill",
    "heir": "Possible heir (as reported)",
}

DOC_TYPES = {
    "death_certificate": "Death certificate",
    "deed": "Recorded deed",
    "tod_affidavit": "Transfer on Death affidavit",
    "will": "Will",
    "tax_bill": "Property tax bill",
    "mortgage_statement": "Mortgage statement",
    "other": "Other document",
}

# (doc_type, words that must all appear in the text, upper case)
CLASSIFY = [
    ("death_certificate", ("CERTIFICATE OF DEATH",)),
    ("tod_affidavit", ("TRANSFER ON DEATH", "AFFIDAVIT")),
    ("will", ("LAST WILL AND TESTAMENT",)),
    ("deed", ("DEED", "GRANTOR")),
    ("tax_bill", ("REAL ESTATE TAX",)),
    ("mortgage_statement", ("MORTGAGE", "STATEMENT")),
]

# Labeled lines the rules know how to read, per document type: (field key, label pattern)
PATTERNS = {
    "death_certificate": [("decedent_name", r"name of decedent"), ("date_of_death", r"date of death"),
                          ("property_address", r"residence address")],
    "deed": [("deed_type", r"deed type"), ("deed_grantees", r"grantees?"), ("parcel_id", r"parcel (?:number|no\.?)"),
             ("property_address", r"property address"), ("recording_date", r"recorded on|recording date"),
             ("instrument_number", r"instrument (?:number|no\.?)")],
    "tod_affidavit": [("deed_grantees", r"owners?"), ("tod_beneficiaries", r"beneficiar(?:y|ies)"),
                      ("parcel_id", r"parcel (?:number|no\.?)"), ("recording_date", r"recorded on|recording date")],
    "will": [("decedent_name", r"testator"), ("will_executor", r"executor"), ("will_date", r"dated|signed on")],
    "tax_bill": [("tax_owner", r"owner(?: name)?"), ("parcel_id", r"parcel (?:number|no\.?)"),
                 ("property_address", r"property (?:address|location)")],
    "mortgage_statement": [("property_address", r"property address")],
}

INSTRUCTION_LIKE = re.compile(r"ignore (?:all |any )?(?:previous|prior|above) instructions|system prompt|you are an? "
                              r"(?:ai|assistant|model)|send (?:an )?(?:email|message) to|approve (?:all|every)|"
                              r"disregard (?:the )?rules", re.I)
MAX_VALUE = 200


@dataclass
class PageText:
    page: int
    text: str


@dataclass
class ReadResult:
    status: str                  # ok, no_text, not_pdf, too_long, error
    pages: list[PageText]


@dataclass
class Proposal:
    key: str
    value: str
    page: int
    evidence: str


@dataclass
class Extraction:
    doc_type: str
    type_evidence: str
    proposals: list[Proposal]
    warnings: list[str]


def read_pdf(data: bytes, max_pages: int) -> ReadResult:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > max_pages:
            return ReadResult("too_long", [])
        found = [PageText(i + 1, (p.extract_text() or "").strip()) for i, p in enumerate(reader.pages)]
    except Exception:                                   # a damaged or encrypted PDF must not stop the upload
        return ReadResult("error", [])
    if sum(len(p.text) for p in found) < 20:
        return ReadResult("no_text", found)            # a scan with no text layer: needs OCR, which isn't set up
    return ReadResult("ok", found)


def _lines(pages: list[PageText]):
    for p in pages:
        for line in p.text.splitlines():
            line = " ".join(line.split())
            if line:
                yield p.page, line


class RuleExtractor:
    """Reads 'Label: value' lines. Offline, free and predictable; also the mock mode for demos and tests."""

    name = "rules"

    def classify(self, pages: list[PageText]) -> tuple[str, str]:
        text = "\n".join(p.text for p in pages).upper()
        for doc_type, words in CLASSIFY:
            if all(w in text for w in words):
                return doc_type, "Contains: " + ", ".join(words)
        return "other", "No known document heading found"

    def extract(self, doc_type: str, pages: list[PageText]) -> list[Proposal]:
        proposals, seen = [], set()
        for page, line in _lines(pages):
            for key, label in PATTERNS.get(doc_type, []):
                match = re.match(rf"^\s*(?:{label})\s*[:\-]\s*(.+)$", line, re.I)
                if match and (key, match.group(1)) not in seen:
                    value = match.group(1).strip()[:MAX_VALUE]
                    seen.add((key, value))
                    proposals.append(Proposal(key, value, page, line[:300]))
        return proposals


def get_extractor(name: str) -> RuleExtractor:
    # Only the rule-based extractor exists today. Unknown names fall back to it rather than failing an upload.
    return RuleExtractor()


def instruction_warnings(pages: list[PageText]) -> list[str]:
    return [f"Page {page}: text that looks like instructions to software was ignored: \"{line[:120]}\""
            for page, line in _lines(pages) if INSTRUCTION_LIKE.search(line)]


def run(extractor: RuleExtractor, pages: list[PageText]) -> Extraction:
    doc_type, evidence = extractor.classify(pages)
    proposals = [p for p in extractor.extract(doc_type, pages) if p.key in FIELD_LABELS]
    return Extraction(doc_type, evidence, proposals, instruction_warnings(pages))


def normalize(value: str | None) -> str:
    """For spotting conflicts only: 'James L. Parker' and 'JAMES L PARKER' compare equal. The stored value is unchanged."""
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())
