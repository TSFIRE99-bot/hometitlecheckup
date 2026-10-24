"""Optional Homestead Benefits Check: which Ohio property tax breaks a family might claim, how much, and how, in Franklin County.

Shown after the title result. The homestead exemption and the owner occupancy credit go to owners on the County record
who live in the home, so a title that isn't settled comes first. Only the County Auditor decides who qualifies.

The savings estimate uses the Auditor's own published schedule for the home's tax district (titlecheck/tax_districts.py).
A Franklin County parcel number starts with its tax district, so the app can look it up without asking.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from statistics import median

from titlecheck.assess import AT_RISK, IN_PROGRESS, NO, PROTECTED, UNSURE, YES, Step
from titlecheck.resources import CONTACTS, HOMESTEAD, link
from titlecheck.tax_districts import DISTRICTS, SCHEDULE_YEAR

SENIOR = "65 or older (or turning 65 this year)"
DISABLED = "Permanently and totally disabled"
SPOUSE = "Surviving spouse of someone who got the exemption (59 or older when they died)"
VETERAN = "Veteran with a 100% service-connected disability rating, or their surviving spouse"
QUALIFIERS = [SENIOR, DISABLED, SPOUSE, VETERAN]
INCOME_TESTED = {SENIOR, DISABLED, SPOUSE}       # the disabled veteran exemption has no income limit

# The disabled veteran exemption takes twice as much of the home's value off ($58,000 vs $29,000), so it saves twice as much
VETERAN_MULTIPLIER = 2
TYPICAL_SAVINGS = int(median(v for _, v in DISTRICTS.values()))
LOWEST_SAVINGS = min(v for _, v in DISTRICTS.values())
HIGHEST_SAVINGS = max(v for _, v in DISTRICTS.values())

EXPLAINER = (f"Ohio's **homestead exemption** lowers property taxes for homeowners who are 65 or older, permanently "
             f"disabled, or a qualifying surviving spouse: the first {HOMESTEAD['exempt_value']} of the home's value "
             f"isn't taxed ({HOMESTEAD['veteran_value']} for veterans with a 100% disability rating). In Franklin "
             f"County that's usually **${LOWEST_SAVINGS} to ${HIGHEST_SAVINGS} a year**. Any owner who lives in the "
             "home can also get a smaller **owner occupancy credit**. Both are free to apply for, through the "
             "Franklin County Auditor.")

CAVEATS = [
    "Eligibility depends on more than these questions, like income, who is on the deed, and where you lived on "
    "January 1. Only the Franklin County Auditor can approve it.",
    "Clearing a title doesn't automatically get you the exemption. It lets you apply; the Auditor still checks every "
    "requirement.",
    "Dollar figures are from the Auditor's website and change every year. Applying is free; never pay anyone to "
    "file it for you.",
]


@dataclass
class HomesteadAnswers:
    main_home: str = UNSURE                 # does an owner live here as their main home?
    gets_it_now: str = UNSURE               # does the home get the homestead exemption now?
    qualifiers: list[str] = field(default_factory=list)  # which of QUALIFIERS fit an owner who lives here
    income_ok: str = UNSURE                 # owner's (and spouse's) income at or under the limit? (asked if it matters)


@dataclass
class Savings:
    yearly: int                     # estimated dollars a year
    district: str | None            # tax district number, like "010"
    district_name: str | None       # the Auditor's name for it, like "City of Columbus"
    veteran: bool = False

    @property
    def source(self) -> str:
        where = (f"tax district {self.district} ({self.district_name})" if self.district
                 else "a typical Franklin County home")
        kind = "disabled veteran exemption" if self.veteran else "homestead exemption"
        return f"The Franklin County Auditor's {SCHEDULE_YEAR} estimate of the {kind} for {where}."


@dataclass
class HomesteadPlan:
    headline: str
    notes: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    caveats: list[str] = field(default_factory=lambda: list(CAVEATS))
    savings: Savings | None = None          # what the family could save if it qualifies
    timeline: list[tuple[str, str]] = field(default_factory=list)   # (when, what happens)


def district_of(parcel_id: str) -> str | None:
    """'010-123456' -> '010' (City of Columbus). None for the demo, typed-in homes, or a number we don't know."""
    code = (parcel_id or "")[:3]
    return code if code in DISTRICTS else None


def district_name(code: str) -> str:
    """'CITY OF COLUMBUS-PLEASANT TWP' -> 'City of Columbus-Pleasant TWP' (keeps the Auditor's abbreviations)."""
    keep = {"CSD", "LSD", "TWP", "COLS", "GPT", "MAD", "L", "RE"}
    words = re.split(r"(\W+)", DISTRICTS[code][0])
    return "".join(w if w in keep or not w.isalpha() else w.lower() if w in ("OF", "THE") else w.capitalize()
                   for w in words)


def estimate(parcel_id: str, veteran: bool = False) -> Savings:
    code = district_of(parcel_id)
    yearly = DISTRICTS[code][1] if code else TYPICAL_SAVINGS
    name = district_name(code) if code else None
    return Savings(yearly * (VETERAN_MULTIPLIER if veteran else 1), code, name, veteran)


# ---------------------------------------------------------------- plan building blocks
def _apply_steps(a: HomesteadAnswers, qualifies: bool) -> list[Step]:
    name, address, phone = CONTACTS["auditor"]
    steps = []
    if a.gets_it_now == UNSURE:
        steps.append(Step("Check what the home gets now",
                          f"Look the home up on the {link('auditor_search')}. The tax section lists a 'Homestead' "
                          "or 'Owner Occupancy' credit if the home already gets one. Your tax bill shows them too.",
                          time="5 minutes online", cost="Free", where="auditor"))
    if VETERAN in a.qualifiers:
        steps.append(Step("Apply for the disabled veteran homestead exemption",
                          f"The first {HOMESTEAD['veteran_value']} of the home's value isn't taxed, with no income "
                          f"limit. Fill out {link('dte_105i')} and include the VA letter showing a 100% rating.",
                          time="About 15 minutes", cost="Free", where="auditor"))
    if INCOME_TESTED & set(a.qualifiers) and qualifies and VETERAN not in a.qualifiers:
        steps.append(Step("Apply for the homestead exemption",
                          f"The first {HOMESTEAD['exempt_value']} of the home's value isn't taxed. New applicants' "
                          f"income ({HOMESTEAD['income_year']} Ohio modified adjusted gross income) must be "
                          f"{HOMESTEAD['income_limit']} or less. Fill out {link('dte_105a')}; a disabled owner also "
                          "needs a doctor to sign the Certificate of Disability (DTE 105E). A surviving spouse who "
                          "already gets it may not need a new form; ask the Auditor.",
                          time="About 15 minutes", cost="Free", where="auditor"))
    steps.append(Step("Apply for the owner occupancy credit",
                      "Any owner who lives in the home as their main home on January 1 can get it, with no age or "
                      f"income limit. It lowers taxes from levies passed in November 2013 or earlier. Fill out "
                      f"{link('dte_105c')}. More: {link('owner_occupancy')}.",
                      time="About 10 minutes", cost="Free", where="auditor"))
    steps.append(Step(f"File by {HOMESTEAD['deadline']}",
                      f"Apply by {HOMESTEAD['deadline']} of the year you want the tax break for. Late applications are "
                      "accepted. You don't reapply every year; the Auditor mails a renewal form each January.",
                      time="Before the deadline", cost="Free"))
    steps.append(Step("Ask the Auditor's office for help",
                      f"{name}, {address}, {phone}. Details and the online form: {link('homestead')}.",
                      time="One phone call", cost="Free", where="auditor"))
    return steps


def _report_changes() -> Step:
    return Step("Tell the Auditor when things change",
                "If the owner who got the tax break dies, sells or moves out, tell the Auditor. It doesn't pass to "
                "heirs (only to a surviving spouse who qualifies), and tax breaks given to someone who no longer "
                f"qualifies may have to be paid back. {CONTACTS['auditor'][0]}: {CONTACTS['auditor'][2]}.",
                time="One phone call", cost="Free", where="auditor")


def _timeline(year: int) -> list[tuple[str, str]]:
    return [(f"By December 31, {year}", "Send the application to the Auditor: online, by mail, or in person."),
            (f"Early {year + 1}", f"The tax bill for {year} taxes (Ohio bills a year behind) should show the lower "
                                  "amount."),
            ("Every January after", "The Auditor mails a renewal form. Read it, and tell the Auditor if anything "
                                    "changed.")]


# ---------------------------------------------------------------- the decision
def homestead_plan(a: HomesteadAnswers, title_status: str, parcel_id: str = "", who: str = "the owner",
                   year: int | None = None) -> HomesteadPlan:
    """What a family can claim, given its answers, the title status from assess(), and the home's parcel number.

    `who` names the owners in plain words ("James and Louise") so the result can speak to this family.
    """
    year = year or date.today().year
    veteran = VETERAN in a.qualifiers
    income_tested = bool(INCOME_TESTED & set(a.qualifiers))
    qualifies = veteran or (income_tested and a.income_ok != NO)
    savings = estimate(parcel_id, veteran) if qualifies else None
    Who = who[:1].upper() + who[1:]

    if a.main_home == NO:
        steps = [_report_changes()] if a.gets_it_now != NO else []
        return HomesteadPlan("These tax breaks are only for the home an owner lives in",
                             ["The homestead exemption and the owner occupancy credit only go to an owner's main home: "
                              "where they lived on January 1, vote, and file income taxes."],
                             steps + [Step("Check again if an owner moves in",
                                           "An owner who makes this their main home can apply for the next year.")])

    notes = []
    if income_tested and a.income_ok == NO and not veteran:
        notes.append(f"With income over {HOMESTEAD['income_limit']}, a new application for the homestead exemption "
                     f"won't qualify. One exception: if {who} already got it for 2013 at this home, the income limit "
                     "doesn't apply. The owner occupancy credit has no income limit.")

    if title_status not in (PROTECTED, AT_RISK):
        notes.insert(0, "The Auditor gives these tax breaks to owners on the County record who live in the home. If "
                        "the home is still in the name of someone who died, the family living there usually can't "
                        "apply until the title is in their name.")
        steps = [Step("Finish the title steps in your action plan first",
                      "Once the County record shows the right owner, come back to these steps.")]
        if a.gets_it_now != NO:
            steps.append(_report_changes())
        headline = ("Finish the title filing, then apply" if title_status == IN_PROGRESS
                    else "Clear the title first, then apply")
        timeline = [("First", "Clear the title, so the County record shows who owns the home now."),
                    ("Then, by December 31", "The owner on the record applies for that year.")]
        return HomesteadPlan(headline, notes, steps + _apply_steps(a, qualifies), savings=savings, timeline=timeline)

    if a.gets_it_now == YES:
        notes.insert(0, "Keep it: the renewal form comes each January.")
        steps = [_report_changes()]
        if a.qualifiers:
            steps.insert(0, Step("Make sure you get everything you qualify for",
                                 f"Check the tax section on the {link('auditor_search')} for both a 'Homestead' and "
                                 f"an 'Owner Occupancy' credit. If one is missing, the Auditor can help: "
                                 f"{CONTACTS['auditor'][2]}.", time="5 minutes online", cost="Free", where="auditor"))
        return HomesteadPlan("The home already gets a homestead tax break", notes, steps, savings=savings)

    if not a.qualifiers:
        notes.append("From your answers, the owner occupancy credit fits now. An owner can apply for the homestead "
                     "exemption in the year they turn 65 or become permanently disabled.")
    headline = (f"{Who} could save about ${savings.yearly:,} a year" if savings
                else "You may be able to lower your property taxes")
    return HomesteadPlan(headline, notes, _apply_steps(a, qualifies), savings=savings, timeline=_timeline(year))
