"""Makes the result speak to this family: their names, who they are to the home, and what the result means for them.

The decision rules in titlecheck/ stay general; this only changes the words around them. The name someone types is
used for this page and their PDF, and is never saved.
"""
from __future__ import annotations

import re

from titlecheck.assess import AT_RISK, IN_PROGRESS, NO, PROTECTED, TANGLED, owner_kind, pretty

OWNER, FAMILY, HELPER = "My own home", "A family member's home", "Someone I'm helping"
ROLES = [OWNER, FAMILY, HELPER]


def clean_name(text: str | None) -> str:
    """Keep a typed first name short and plain: letters, spaces, hyphens and apostrophes."""
    return re.sub(r"[^A-Za-zÀ-ɏ' -]", "", text or "").strip()[:30]


def first_names(owners: list[str]) -> list[str]:
    """County style 'PARKER JAMES L' -> 'James'. Only for people; trusts and estates are left out."""
    return [pretty(o).split()[0] for o in owners if owner_kind(o) == "person" and pretty(o).split()]


def join(names: list[str], word: str = "and") -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} {word} {names[-1]}"


def owners_phrase(owners: list[str], word: str = "and", role: str = FAMILY) -> str:
    """'James and Louise', or 'you' when the person checking owns the home alone, or 'the owner' if no people."""
    names = first_names(owners)
    if role == OWNER and len(names) <= 1:
        return "you"
    return join(names, word) or "the owner"


def greeting(name: str) -> str:
    return f"{name}, here's your plan" if name else "Here's your plan"


def summary(status: str, role: str, owners: list[str], alive: dict[str, str]) -> str:
    """Two or three plain sentences: what this result means for the person reading it."""
    names = first_names(owners)
    everyone = join(names) or "the owner"
    died = [n for o, n in zip([o for o in owners if owner_kind(o) == "person"], names) if alive.get(o) == NO]
    gone = join(died) or "the owner"
    yours = "your" if role in (OWNER, FAMILY) else "their"
    family = "your family" if role in (OWNER, FAMILY) else "the family"

    if status == PROTECTED:
        return (f"Good news: {yours} home has a plan. When the time comes, it can pass to the people named without "
                "probate court. Keep the paperwork up to date when life changes.")
    if status == AT_RISK:
        if role == OWNER:
            return ("Right now the home is safely in your name. But nothing on record says who gets it next, so "
                    f"{family} could need probate court to keep it. One form, recorded while you're alive, "
                    "prevents that, and it only takes an afternoon.")
        return (f"{everyone} still own{'s' if len(names) == 1 else ''} the home, and that's good. But nothing on "
                f"record says who gets it next, so {family} could end up in probate court. The fix is one form "
                f"{everyone} can sign now, while it's easy.")
    if status == IN_PROGRESS:
        return (f"{family.capitalize()} is on the way to a clear title. There's usually just one filing left. "
                "Finish it soon, so the County record matches who really owns the home.")
    if status == TANGLED:
        return (f"The home is probably still legally in {gone}'s name. That's very common, and it can be fixed. "
                f"Until it is, {family} may not be able to sell, refinance, get repair loans or claim tax breaks. "
                "Ohio has shorter court options for many families, and free legal help is available.")
    return ("We need one more answer before we can say where things stand. The first step below shows how to find "
            "it, and it usually takes one phone call or a few minutes online.")
