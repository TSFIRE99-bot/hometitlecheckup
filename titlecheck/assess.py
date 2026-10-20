"""Turns the property record plus a family's answers into a status and a plain-English action plan.

This is general information about Ohio law, not legal advice. Every plan ends with free legal help.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from titlecheck.resources import CONTACTS, FACTS, link

YES, NO, UNSURE = "Yes", "No", "Not sure"

# Status codes, from best to worst
PROTECTED = "protected"
IN_PROGRESS = "in_progress"
AT_RISK = "at_risk"
TANGLED = "tangled"
CHECK = "check"

STATUS_TEXT = {
    PROTECTED: ("Looks protected", "green"),
    IN_PROGRESS: ("On the way to a clear title", "blue"),
    AT_RISK: ("Not protected yet", "orange"),
    TANGLED: ("Likely tangled title", "red"),
    CHECK: ("We need a little more information", "gray"),
}

NOT_SURE = UNSURE
ESTATE_SIZES = ["Under $35,000", "$35,000 to $100,000", "Over $100,000", NOT_SURE]
ORG_WORDS = {"LLC", "INC", "CORP", "CO", "COMPANY", "BANK", "COUNTY", "CHURCH", "ASSOCIATION", "ASSN",
             "AUTHORITY", "PARTNERSHIP", "LTD", "LP", "COMM", "CITY", "STATE", "VILLAGE", "TOWNSHIP", "SCHOOL"}
TRUST_WORDS = {"TRUST", "TR", "TRUSTEE", "TRUSTEES", "TRS", "TTEE"}


@dataclass
class Answers:
    owners_alive: dict[str, str]          # owner name -> Yes / No / Not sure ("Is this person living?")
    tod_recorded: str = UNSURE            # Transfer on Death affidavit recorded for the home?
    survivorship: str = UNSURE            # deed says "with right of survivorship"? (only matters with 2+ owners)
    probate_opened: str = UNSURE          # has a probate case been opened for the person who died?
    spouse_gets_all: str = UNSURE         # is a surviving spouse inheriting everything?
    estate_size: str = NOT_SURE           # rough value of everything the person left, house included
    only_real_estate: str = UNSURE        # did they leave only the house (no bank accounts, cars, etc.)?


@dataclass
class Step:
    title: str
    detail: str


@dataclass
class Assessment:
    status: str
    headline: str
    reasons: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)

    @property
    def label(self) -> str:
        return STATUS_TEXT[self.status][0]

    @property
    def color(self) -> str:
        return STATUS_TEXT[self.status][1]


def owner_kind(name: str) -> str:
    """'person', 'trust', 'estate' or 'organization', from how the County writes the owner name."""
    words = set(re.findall(r"[A-Z]+", name.upper()))
    if "ESTATE" in words:
        return "estate"
    if words & ORG_WORDS and not words & {"TRUSTEE", "TTEE"}:
        return "organization"
    if words & TRUST_WORDS:
        return "trust"
    return "person"


def record_notes(owners: list[str], years_since_transfer: int | None) -> list[str]:
    """Facts from the County record worth pointing out, before any questions are answered."""
    notes = []
    kinds = [owner_kind(o) for o in owners]
    if "estate" in kinds:
        notes.append("The County lists an **estate** as the owner. That usually means the owner died and the "
                     "home has not been transferred to the heirs yet.")
    if "trust" in kinds:
        notes.append("The home is held in a **trust**. A trust usually passes property without probate, "
                     "as long as a successor trustee is named.")
    if years_since_transfer is not None and years_since_transfer >= 25:
        notes.append(f"The deed hasn't changed hands in about **{years_since_transfer} years**. That's common and "
                     "fine, but if the people named on it have passed away, this is how tangled titles start.")
    if len(owners) >= 2:
        notes.append(f"There are **{len(owners)} owners** on the record. Each one's share has to be accounted for.")
    return notes


# ---------------------------------------------------------------- plan building blocks
def _tod_steps() -> list[Step]:
    return [
        Step("Fill out a Transfer on Death Designation Affidavit",
             f"It names who gets the home when the owner dies, with no probate. Free forms: {link('tod_forms')}. "
             "If the owner is married, the spouse signs too."),
        Step("Sign it in front of a notary",
             "Ohio law requires it to be signed in front of someone who can give oaths, like a notary. "
             "Banks and the County Auditor's office often have one."),
        Step("Record it with the County Recorder before the owner dies",
             f"{CONTACTS['recorder'][0]}, {CONTACTS['recorder'][1]}, {CONTACTS['recorder'][2]}. "
             "There is a small recording fee; check the Recorder's fee calculator. It only works if it is recorded "
             "while the owner is alive. The owner can change or cancel it later."),
    ]


def _confirm_tod_steps() -> list[Step]:
    return [
        Step("File the confirmation affidavit with a death certificate",
             f"The person named on the Transfer on Death affidavit files an affidavit confirming the transfer, "
             f"plus a certified death certificate, with the County Recorder ({link('orc_confirm')}). "
             f"The forms are with the other TOD forms: {link('tod_forms')}."),
        Step("Update the Auditor's records", "Bring a copy to the County Auditor so tax bills and the "
             "homestead tax break go to the new owner."),
    ]


def _survivorship_steps() -> list[Step]:
    return [Step("File the survivorship affidavit with a death certificate",
                 "When a deed says 'with right of survivorship', the living owner keeps the home. "
                 "They file an affidavit and a certified death certificate with the County Auditor and Recorder so "
                 "the record shows them as the owner.")]


def _probate_steps(a: Answers) -> list[Step]:
    steps = []
    small = (a.estate_size == "Under $35,000" or
             (a.estate_size in ("Under $35,000", "$35,000 to $100,000") and a.spouse_gets_all == YES))
    if small:
        steps.append(Step("You may qualify for a simpler 'Release from Administration'",
                          "Franklin County Probate Court has a shorter process for small estates: up to $35,000 with "
                          "no surviving spouse, or up to $100,000 when a surviving spouse inherits everything. "
                          f"Details: {link('probate_small')}."))
    elif a.only_real_estate == YES:
        steps.append(Step("Ask about the 'Real Estate Transfer Only' option",
                          "If the person died more than six months ago, owned only real estate, and no creditors "
                          f"have filed claims, the Probate Court has a real-estate-only option. {link('probate_small')}"))
    else:
        steps.append(Step("Open a probate case to transfer the home",
                          "The Probate Court names someone to handle the estate, then transfers the home to the "
                          f"heirs. It often takes six months to a year. {link('probate_guide')}"))
    steps.append(Step("Gather the papers the court asks for",
                      "Photo ID, a certified death certificate, the original will if there is one, proof the funeral "
                      "was paid, and the deed or tax bill for the home."))
    steps.append(Step("Keep paying the property taxes",
                      "Taxes are still due while the title is being fixed. Unpaid taxes can lead to foreclosure, "
                      "even on an inherited home."))
    return steps


def _legal_help() -> Step:
    name, web, phone = CONTACTS["lasco"]
    return Step("Get free legal help",
                f"{name} helps low-income families for free: {link('lasco')} or {phone}. "
                f"Probate Court clerks can explain the steps at {CONTACTS['probate'][2]}, but can't give legal advice. "
                f"Plain-English guide: {link('ohio_legal_help_probate')}.")


# ---------------------------------------------------------------- the decision
def assess(owners: list[str], answers: Answers) -> Assessment:
    kinds = {o: owner_kind(o) for o in owners}
    people = [o for o in owners if kinds[o] == "person"]

    if owners and all(k == "organization" for k in kinds.values()):
        return Assessment(CHECK, "This home is owned by a company or organization",
                          ["This tool is for homes owned by people or families."], [_legal_help()])

    if any(k == "trust" for k in kinds.values()) and not people:
        return Assessment(PROTECTED, "The home is held in a trust",
                          ["Trusts usually pass a home without probate."],
                          [Step("Make sure a successor trustee is named",
                                "The trust document should say who takes over when the current trustee dies. "
                                "If nobody is named, or the trust was never finished, talk to a lawyer."),
                           _legal_help()])

    if any(k == "estate" for k in kinds.values()):
        if answers.probate_opened == YES:
            return Assessment(IN_PROGRESS, "A probate case is handling the transfer",
                              ["The County lists an estate as the owner, and you said probate has been opened."],
                              [Step("Follow the case to the end",
                                    "When the court approves it, the home is transferred to the heirs and the County "
                                    "record changes. Ask the court or your lawyer what is still needed."),
                               Step("Keep paying the property taxes",
                                    "Taxes are still due while the case is open."), _legal_help()])
        return Assessment(TANGLED, "The home is still in an estate's name",
                          ["The County lists an estate as the owner, and no probate case has been opened."],
                          _probate_steps(answers) + [_legal_help()])

    alive = [answers.owners_alive.get(p, UNSURE) for p in people]
    if not people:
        return Assessment(CHECK, "We couldn't tell who owns this home", [], [_legal_help()])

    if UNSURE in alive and NO not in alive:
        return Assessment(CHECK, "First, find out whether everyone on the deed is living",
                          ["The answer decides everything else."],
                          [Step("Check with family", "Ask relatives whether each person on the deed is living."),
                           _legal_help()])

    deceased = [p for p, s in zip(people, alive) if s == NO]
    living = [p for p, s in zip(people, alive) if s == YES]

    # Everyone on the deed is alive: protect the home now
    if not deceased:
        if answers.tod_recorded == YES:
            return Assessment(PROTECTED, "The home has a plan for what happens next",
                              ["Everyone on the deed is living, and a Transfer on Death affidavit is recorded."],
                              [Step("Keep it up to date",
                                    "If a named person dies or family plans change, record a new affidavit."),
                               Step("Tell the people named",
                                    "They'll need to file a confirmation affidavit and a death certificate later.")])
        reasons = ["Everyone on the deed is living, but nothing is recorded that says who gets the home next."]
        if answers.tod_recorded == UNSURE:
            reasons.append(f"You can check for a recorded affidavit at the {link('recorder_search')}.")
        return Assessment(AT_RISK, "Protect the home now, while it's easy", reasons,
                          _tod_steps() + [_legal_help()])

    # Someone on the deed has died
    if len(people) == 1:
        reasons = ["The person on the deed has passed away."]
    elif len(deceased) == len(people):
        reasons = [f"All {len(people)} people on the deed have passed away."]
    else:
        reasons = [f"{len(deceased)} of the {len(people)} people on the deed "
                   f"{'has' if len(deceased) == 1 else 'have'} passed away."]
    steps: list[Step] = []
    if living and answers.survivorship == YES:
        reasons.append("The deed gives the surviving owner(s) the home (right of survivorship).")
        steps += _survivorship_steps()
        if answers.tod_recorded != YES:
            steps += _tod_steps()
        return Assessment(IN_PROGRESS, "The surviving owner can clear the title with one filing",
                          reasons, steps + [_legal_help()])
    if answers.tod_recorded == YES:
        reasons.append("A Transfer on Death affidavit was recorded before the death.")
        return Assessment(IN_PROGRESS, "The named family member can finish the transfer",
                          reasons, _confirm_tod_steps() + [_legal_help()])
    if answers.probate_opened == YES:
        reasons.append("A probate case has been opened.")
        return Assessment(IN_PROGRESS, "A probate case is handling the transfer", reasons,
                          [Step("Follow the case to the end", "Ask the court or your lawyer what is still needed."),
                           Step("Keep paying the property taxes", "Taxes are still due while the case is open."),
                           _legal_help()])
    if UNSURE in (answers.tod_recorded, answers.survivorship if living else NO):
        reasons.append("We couldn't confirm whether a Transfer on Death affidavit or survivorship deed exists.")
        return Assessment(CHECK, "Check the recorded deed before doing anything else", reasons,
                          [Step("Look up the recorded documents",
                                f"Search the address or owner at the {link('recorder_search')} for a 'Transfer on "
                                "Death Designation Affidavit' or a deed that says 'survivorship'. The Recorder's "
                                f"office can help: {CONTACTS['recorder'][2]}."),
                           _legal_help()])
    reasons.append("Nothing was recorded to pass the home on, and no probate case is open.")
    return Assessment(TANGLED, "The home is probably still legally in the name of someone who died", reasons,
                      _probate_steps(answers) + [_legal_help()])


def why_it_matters() -> list[str]:
    return [FACTS["blocked"], FACTS["ohio_count"], FACTS["ohio_value"]]
