"""Follow-up messages to family members.

Rules for the pilot: only templates an attorney or owner approved can be used; a person must have agreed to email
before anything is addressed to them; the same template to the same person is blocked for a set number of hours; and a
staff member presses Send every time. Nothing is generated or sent automatically. Until an email provider is
authorized, "sending" records the message in the outbox only.
"""
from __future__ import annotations

import re

DEFAULT_TEMPLATES = (
    ("Documents still needed",
     "Documents still needed for {case_title}",
     "Hello {name},\n\nThank you for helping with {case_title}. We still need:\n\n{missing_list}\n\n"
     "You can upload them securely here: {link}\nThe link works until {link_expires}.\n\n"
     "If you have questions, reply to this email or call our office.\n\n{firm_name}"),
    ("Thank you, documents received",
     "We received your documents for {case_title}",
     "Hello {name},\n\nWe received what you uploaded for {case_title}. Our staff will review it and contact you if "
     "anything else is needed.\n\n{firm_name}"),
)

PLACEHOLDER = re.compile(r"\{(\w+)\}")
ALLOWED = {"name", "case_title", "missing_list", "link", "link_expires", "firm_name"}


def unknown_placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER.findall(text)) - ALLOWED


def render(text: str, values: dict) -> str:
    # Only known placeholders are filled; anything else stays as written, so template text can't reach other data.
    return PLACEHOLDER.sub(lambda m: str(values.get(m.group(1), m.group(0))) if m.group(1) in ALLOWED else m.group(0),
                           text)
