"""Turns the property record plus a family's answers into a status and a plain-English action plan.

This is general information about Ohio law, not legal advice. Every plan ends with free legal help.
Every sentence goes through t() so it can be shown in Spanish or Somali (titlecheck/i18n.py); the decisions don't change.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from titlecheck.i18n import N_, t
from titlecheck.resources import CONTACTS, FACTS, FEES, link

# The answers are stored in English (the decisions compare them); the screen shows t(YES) and so on
YES, NO, UNSURE = N_("Yes"), N_("No"), N_("Not sure")

# Status codes, from best to worst
PROTECTED = "protected"
IN_PROGRESS = "in_progress"
AT_RISK = "at_risk"
TANGLED = "tangled"
CHECK = "check"

STATUS_TEXT = {
    PROTECTED: (N_("Looks protected"), "green"),
    IN_PROGRESS: (N_("On the way to a clear title"), "blue"),
    AT_RISK: (N_("Not protected yet"), "orange"),
    TANGLED: (N_("Likely tangled title"), "red"),
    CHECK: (N_("We need a little more information"), "gray"),
}

NOT_SURE = UNSURE
ESTATE_SIZES = [N_("Under $35,000"), N_("$35,000 to $100,000"), N_("Over $100,000"), NOT_SURE]
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
    time: str = ""          # roughly how long it takes, in plain words
    cost: str = ""          # what it costs, if anything
    where: str = ""         # key of the office in titlecheck/places.py that helps with it, if any


@dataclass
class Assessment:
    status: str
    headline: str
    reasons: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)

    @property
    def label(self) -> str:
        return t(STATUS_TEXT[self.status][0])

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


def pretty(name: str) -> str:
    """County style 'PARKER JAMES L' -> 'James L Parker' (people only)."""
    if owner_kind(name) != "person":
        return name.title()
    parts = name.title().split()
    return " ".join(parts[1:] + parts[:1]) if len(parts) > 1 else name.title()


def record_notes(owners: list[str], years_since_transfer: int | None) -> list[str]:
    """Facts from the County record worth pointing out, before any questions are answered."""
    notes = []
    kinds = [owner_kind(o) for o in owners]
    if "estate" in kinds:
        notes.append(t("The County lists an **estate** as the owner. That usually means the owner died and the "
                       "home has not been transferred to the heirs yet."))
    if "trust" in kinds:
        notes.append(t("The home is held in a **trust**. A trust usually passes property without probate, "
                       "as long as a successor trustee is named."))
    if years_since_transfer is not None and years_since_transfer >= 25:
        notes.append(t("The deed hasn't changed hands in about **{years} years**. That's common and fine, but if the "
                       "people named on it have passed away, this is how tangled titles start.",
                       years=years_since_transfer))
    if len(owners) >= 2:
        notes.append(t("There are **{n} owners** on the record. Each one's share has to be accounted for.",
                       n=len(owners)))
    return notes


# ---------------------------------------------------------------- plan building blocks
def _tod_steps() -> list[Step]:
    return [
        Step(t("Fill out a Transfer on Death Designation Affidavit"),
             t("It names who gets the home when the owner dies, with no probate. Free forms: {forms}. "
               "If the owner is married, the spouse signs too.", forms=link("tod_forms")),
             time=t("About 30 minutes"), cost=t("Free form"), where="law_library"),
        Step(t("Sign it in front of a notary"),
             t("Ohio law requires it to be signed in front of someone who can give oaths, like a notary. "
               "Banks and the County Auditor's office often have one."),
             time=t("About 15 minutes"), cost=t("Often free at your bank or credit union")),
        Step(t("Record it with the County Recorder before the owner dies"),
             t("{office}, {address}, {phone}. The recording fee is {fee}. It only works if it is recorded while the "
               "owner is alive. The owner can change or cancel it later.", office=CONTACTS["recorder"][0],
               address=CONTACTS["recorder"][1], phone=CONTACTS["recorder"][2], fee=t(FEES["recording"])),
             time=t("One visit, or by mail"), cost=t(FEES["recording_short"]), where="recorder"),
    ]


def _confirm_tod_steps() -> list[Step]:
    return [
        Step(t("File the confirmation affidavit with a death certificate"),
             t("The person named on the Transfer on Death affidavit files an affidavit confirming the transfer, plus "
               "a certified death certificate, with the County Recorder ({law}). The forms are with the other TOD "
               "forms: {forms}.", law=link("orc_confirm"), forms=link("tod_forms")),
             time=t("One visit"), cost=t(FEES["recording_short"]), where="recorder"),
        Step(t("Update the Auditor's records"),
             t("Bring a copy to the County Auditor so tax bills and the homestead tax break go to the new owner."),
             time=t("One visit"), cost=t("Free"), where="auditor"),
    ]


def _survivorship_steps() -> list[Step]:
    return [Step(t("File the survivorship affidavit with a death certificate"),
                 t("When a deed says 'with right of survivorship', the living owner keeps the home. They file an "
                   "affidavit and a certified death certificate with the County Auditor and Recorder so the record "
                   "shows them as the owner."),
                 time=t("One visit"), cost=t(FEES["recording_short"]), where="recorder")]


def _probate_steps(a: Answers) -> list[Step]:
    steps = []
    small = (a.estate_size == "Under $35,000" or
             (a.estate_size in ("Under $35,000", "$35,000 to $100,000") and a.spouse_gets_all == YES))
    if small:
        steps.append(Step(t("You may qualify for a simpler 'Release from Administration'"),
                          t("Franklin County Probate Court has a shorter process for small estates: up to $35,000 "
                            "with no surviving spouse, or up to $100,000 when a surviving spouse inherits everything. "
                            "Details: {brochure}.", brochure=link("probate_small")),
                          time=t("Usually faster than full probate"), cost=t(FEES["court"]), where="probate"))
    elif a.only_real_estate == YES:
        steps.append(Step(t("Ask about the 'Real Estate Transfer Only' option"),
                          t("If the person died more than six months ago, owned only real estate, and no creditors "
                            "have filed claims, the Probate Court has a real-estate-only option. {brochure}",
                            brochure=link("probate_small")),
                          time=t("Usually faster than full probate"), cost=t(FEES["court"]), where="probate"))
    else:
        steps.append(Step(t("Open a probate case to transfer the home"),
                          t("The Probate Court names someone to handle the estate, then transfers the home to the "
                            "heirs. It often takes six months to a year. {guide}", guide=link("probate_guide")),
                          time=t("Often 6 to 12 months"), cost=t(FEES["court"]), where="probate"))
    steps.append(Step(t("Gather the papers the court asks for"),
                      t("Photo ID, a certified death certificate, the original will if there is one, proof the "
                        "funeral was paid, and the deed or tax bill for the home."),
                      time=t("A few days"), cost=t("Small fee for each certified death certificate")))
    steps.append(_keep_paying(t("Taxes are still due while the title is being fixed. Unpaid taxes can lead to "
                                "foreclosure, even on an inherited home.")))
    return steps


def _keep_paying(detail: str) -> Step:
    return Step(t("Keep paying the property taxes"), detail, time=t("Twice a year"), where="auditor")


def _follow_case(detail: str) -> Step:
    return Step(t("Follow the case to the end"), detail, where="probate")


def _legal_help() -> Step:
    name, web, phone = CONTACTS["lasco"]
    return Step(t("Get free legal help"),
                t("{name} helps low-income families for free: {apply}, or call the intake line at {intake} ({hours}). "
                  "Probate Court clerks can explain the steps at {probate}, but can't give legal advice. "
                  "Plain-English guide: {guide}.", name=name, apply=link("lasco"),
                  intake=CONTACTS["lasco_intake"][2], hours=t(CONTACTS["lasco_intake"][1]),
                  probate=CONTACTS["probate"][2], guide=link("ohio_legal_help_probate")),
                time=t("One phone call to start"), cost=t("Free if you qualify"), where="lasco")


# ---------------------------------------------------------------- the decision
def assess(owners: list[str], answers: Answers) -> Assessment:
    kinds = {o: owner_kind(o) for o in owners}
    people = [o for o in owners if kinds[o] == "person"]

    if owners and all(k == "organization" for k in kinds.values()):
        return Assessment(CHECK, t("This home is owned by a company or organization"),
                          [t("This tool is for homes owned by people or families.")], [_legal_help()])

    if any(k == "trust" for k in kinds.values()) and not people:
        return Assessment(PROTECTED, t("The home is held in a trust"),
                          [t("Trusts usually pass a home without probate.")],
                          [Step(t("Make sure a successor trustee is named"),
                                t("The trust document should say who takes over when the current trustee dies. "
                                  "If nobody is named, or the trust was never finished, talk to a lawyer.")),
                           _legal_help()])

    if any(k == "estate" for k in kinds.values()):
        if answers.probate_opened == YES:
            return Assessment(IN_PROGRESS, t("A probate case is handling the transfer"),
                              [t("The County lists an estate as the owner, and you said probate has been opened.")],
                              [_follow_case(t("When the court approves it, the home is transferred to the heirs and "
                                              "the County record changes. Ask the court or your lawyer what is still "
                                              "needed.")),
                               _keep_paying(t("Taxes are still due while the case is open.")), _legal_help()])
        return Assessment(TANGLED, t("The home is still in an estate's name"),
                          [t("The County lists an estate as the owner, and no probate case has been opened.")],
                          _probate_steps(answers) + [_legal_help()])

    alive = [answers.owners_alive.get(p, UNSURE) for p in people]
    if not people:
        return Assessment(CHECK, t("We couldn't tell who owns this home"), [], [_legal_help()])

    if UNSURE in alive and NO not in alive:
        return Assessment(CHECK, t("First, find out whether everyone on the deed is living"),
                          [t("The answer decides everything else.")],
                          [Step(t("Check with family"), t("Ask relatives whether each person on the deed is living."),
                                time=t("A phone call"), cost=t("Free")),
                           _legal_help()])

    deceased = [p for p, s in zip(people, alive) if s == NO]
    living = [p for p, s in zip(people, alive) if s == YES]

    # Everyone on the deed is alive: protect the home now
    if not deceased:
        if answers.tod_recorded == YES:
            return Assessment(PROTECTED, t("The home has a plan for what happens next"),
                              [t("Everyone on the deed is living, and a Transfer on Death affidavit is recorded.")],
                              [Step(t("Keep it up to date"),
                                    t("If a named person dies or family plans change, record a new affidavit."),
                                    cost=t(FEES["recording_short"]), where="recorder"),
                               Step(t("Tell the people named"),
                                    t("They'll need to file a confirmation affidavit and a death certificate later."),
                                    time=t("One conversation"), cost=t("Free"))])
        reasons = [t("Everyone on the deed is living, but nothing is recorded that says who gets the home next.")]
        if answers.tod_recorded == UNSURE:
            reasons.append(t("You can check for a recorded affidavit at the {search}.", search=link("recorder_search")))
        return Assessment(AT_RISK, t("Protect the home now, while it's easy"), reasons,
                          _tod_steps() + [_legal_help()])

    # Someone on the deed has died
    if len(people) == 1:
        reasons = [t("The person on the deed has passed away.")]
    elif len(deceased) == len(people):
        reasons = [t("All {n} people on the deed have passed away.", n=len(people))]
    elif len(deceased) == 1:
        reasons = [t("1 of the {n} people on the deed has passed away.", n=len(people))]
    else:
        reasons = [t("{died} of the {n} people on the deed have passed away.", died=len(deceased), n=len(people))]
    steps: list[Step] = []
    if living and answers.survivorship == YES:
        reasons.append(t("The deed gives the surviving owner(s) the home (right of survivorship)."))
        steps += _survivorship_steps()
        if answers.tod_recorded != YES:
            steps += _tod_steps()
        return Assessment(IN_PROGRESS, t("The surviving owner can clear the title with one filing"),
                          reasons, steps + [_legal_help()])
    if answers.tod_recorded == YES:
        reasons.append(t("A Transfer on Death affidavit was recorded before the death."))
        return Assessment(IN_PROGRESS, t("The named family member can finish the transfer"),
                          reasons, _confirm_tod_steps() + [_legal_help()])
    if answers.probate_opened == YES:
        reasons.append(t("A probate case has been opened."))
        return Assessment(IN_PROGRESS, t("A probate case is handling the transfer"), reasons,
                          [_follow_case(t("Ask the court or your lawyer what is still needed.")),
                           _keep_paying(t("Taxes are still due while the case is open.")),
                           _legal_help()])
    if UNSURE in (answers.tod_recorded, answers.survivorship if living else NO):
        reasons.append(t("We couldn't confirm whether a Transfer on Death affidavit or survivorship deed exists."))
        return Assessment(CHECK, t("Check the recorded deed before doing anything else"), reasons,
                          [Step(t("Look up the recorded documents"),
                                t("Search the address or owner at the {search} for a 'Transfer on Death Designation "
                                  "Affidavit' or a deed that says 'survivorship'. The Recorder's office can help: "
                                  "{phone}.", search=link("recorder_search"), phone=CONTACTS["recorder"][2]),
                                time=t("About 15 minutes online"), cost=t("Free to search"), where="recorder"),
                           _legal_help()])
    reasons.append(t("Nothing was recorded to pass the home on, and no probate case is open."))
    return Assessment(TANGLED, t("The home is probably still legally in the name of someone who died"), reasons,
                      _probate_steps(answers) + [_legal_help()])


def why_it_matters() -> list[str]:
    return [t(FACTS["blocked"]), t(FACTS["ohio_count"]), t(FACTS["ohio_value"])]
