"""Makes the result speak to this family: their names, who they are to the home, and what the result means for them.

The decision rules in titlecheck/ stay general; this only changes the words around them. The name someone types is
used for this page and their PDF, and is never saved. Every sentence goes through t() (titlecheck/i18n.py).
"""
from __future__ import annotations

import re

from titlecheck.assess import AT_RISK, IN_PROGRESS, NO, PROTECTED, TANGLED, owner_kind, pretty
from titlecheck.i18n import N_, t

# Stored in English (the code compares them); the screen shows t(OWNER) and so on
OWNER, FAMILY, HELPER = N_("My own home"), N_("A family member's home"), N_("Someone I'm helping")
ROLES = [OWNER, FAMILY, HELPER]


def clean_name(text: str | None) -> str:
    """Keep a typed first name short and plain: letters, spaces, hyphens and apostrophes."""
    return re.sub(r"[^A-Za-zÀ-ɏ' -]", "", text or "").strip()[:30]


def first_names(owners: list[str]) -> list[str]:
    """County style 'PARKER JAMES L' -> 'James'. Only for people; trusts and estates are left out."""
    return [pretty(o).split()[0] for o in owners if owner_kind(o) == "person" and pretty(o).split()]


def join(names: list[str], word: str = "and") -> str:
    """['James', 'Louise'] -> 'James and Louise' ('y' in Spanish, 'iyo' in Somali). word is 'and' or 'or'."""
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    joiner = t("and") if word == "and" else t("or")
    return f"{', '.join(names[:-1])} {joiner} {names[-1]}"


def owners_phrase(owners: list[str], word: str = "and", role: str = FAMILY) -> str:
    """'James and Louise', or 'you' when the person checking owns the home alone, or 'the owner' if no people.

    'you' and 'the owner' stay in English here; they're signals that the caller turns into full translated sentences.
    """
    names = first_names(owners)
    if role == OWNER and len(names) <= 1:
        return "you"
    return join(names, word) or "the owner"


def greeting(name: str) -> str:
    return t("{name}, here's your plan", name=name) if name else t("Here's your plan")


def summary(status: str, role: str, owners: list[str], alive: dict[str, str]) -> str:
    """Two or three plain sentences: what this result means for the person reading it."""
    names = first_names(owners)
    everyone = join(names)
    died = [n for o, n in zip([o for o in owners if owner_kind(o) == "person"], names) if alive.get(o) == NO]
    gone = join(died)
    mine = role in (OWNER, FAMILY)

    if status == PROTECTED:
        return (t("Good news: your home has a plan. When the time comes, it can pass to the people named without "
                  "probate court. Keep the paperwork up to date when life changes.") if mine else
                t("Good news: their home has a plan. When the time comes, it can pass to the people named without "
                  "probate court. Keep the paperwork up to date when life changes."))
    if status == AT_RISK:
        if role == OWNER:
            return t("Right now the home is safely in your name. But nothing on record says who gets it next, so your "
                     "family could need probate court to keep it. One form, recorded while you're alive, prevents "
                     "that, and it only takes an afternoon.")
        family = t("your family") if mine else t("the family")
        if not names:
            return t("The owner still owns the home, and that's good. But nothing on record says who gets it next, so "
                     "{family} could end up in probate court. The fix is one form the owner can sign now, while it's "
                     "easy.", family=family)
        if len(names) == 1:
            return t("{name} still owns the home, and that's good. But nothing on record says who gets it next, so "
                     "{family} could end up in probate court. The fix is one form {name} can sign now, while it's "
                     "easy.", name=everyone, family=family)
        return t("{names} still own the home, and that's good. But nothing on record says who gets it next, so "
                 "{family} could end up in probate court. The fix is one form {names} can sign now, while it's easy.",
                 names=everyone, family=family)
    if status == IN_PROGRESS:
        return (t("Your family is on the way to a clear title. There's usually just one filing left. Finish it soon, "
                  "so the County record matches who really owns the home.") if mine else
                t("The family is on the way to a clear title. There's usually just one filing left. Finish it soon, "
                  "so the County record matches who really owns the home."))
    if status == TANGLED:
        family = t("your family") if mine else t("the family")
        if gone:
            return t("The home is probably still legally in {name}'s name. That's very common, and it can be fixed. "
                     "Until it is, {family} may not be able to sell, refinance, get repair loans or claim tax breaks. "
                     "Ohio has shorter court options for many families, and free legal help is available.",
                     name=gone, family=family)
        return t("The home is probably still legally in the name of the owner who died. That's very common, and it "
                 "can be fixed. Until it is, {family} may not be able to sell, refinance, get repair loans or claim "
                 "tax breaks. Ohio has shorter court options for many families, and free legal help is available.",
                 family=family)
    return t("We need one more answer before we can say where things stand. The first step below shows how to find "
             "it, and it usually takes one phone call or a few minutes online.")
