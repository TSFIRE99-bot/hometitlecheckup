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
from titlecheck.i18n import N_, t
from titlecheck.resources import CONTACTS, HOMESTEAD, link
from titlecheck.tax_districts import DISTRICTS, SCHEDULE_YEAR

# The answers are stored in English; the screen shows t(SENIOR) and so on
SENIOR = N_("65 or older (or turning 65 this year)")
DISABLED = N_("Permanently and totally disabled")
SPOUSE = N_("Surviving spouse of someone who got the exemption (59 or older when they died)")
VETERAN = N_("Veteran with a 100% service-connected disability rating, or their surviving spouse")
QUALIFIERS = [SENIOR, DISABLED, SPOUSE, VETERAN]
INCOME_TESTED = {SENIOR, DISABLED, SPOUSE}       # the disabled veteran exemption has no income limit

# The disabled veteran exemption takes twice as much of the home's value off ($58,000 vs $29,000), so it saves twice as much
VETERAN_MULTIPLIER = 2
TYPICAL_SAVINGS = int(median(v for _, v in DISTRICTS.values()))
LOWEST_SAVINGS = min(v for _, v in DISTRICTS.values())
HIGHEST_SAVINGS = max(v for _, v in DISTRICTS.values())

CAVEATS = [
    N_("Eligibility depends on more than these questions, like income, who is on the deed, and where you lived on "
       "January 1. Only the Franklin County Auditor can approve it."),
    N_("Clearing a title doesn't automatically get you the exemption. It lets you apply; the Auditor still checks every "
       "requirement."),
    N_("Dollar figures are from the Auditor's website and change every year. Applying is free; never pay anyone to "
       "file it for you."),
]


def explainer() -> str:
    return t("Ohio's **homestead exemption** lowers property taxes for homeowners who are 65 or older, permanently "
             "disabled, or a qualifying surviving spouse: the first {exempt} of the home's value isn't taxed "
             "({veteran} for veterans with a 100% disability rating). In Franklin County that's usually **${low} to "
             "${high} a year**. Any owner who lives in the home can also get a smaller **owner occupancy credit**. "
             "Both are free to apply for, through the Franklin County Auditor.",
             exempt=HOMESTEAD["exempt_value"], veteran=HOMESTEAD["veteran_value"], low=LOWEST_SAVINGS,
             high=HIGHEST_SAVINGS)


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
        kind = t("disabled veteran exemption") if self.veteran else t("homestead exemption")
        if self.district:
            return t("The Franklin County Auditor's {year} estimate of the {kind} for tax district {code} ({name}).",
                     year=SCHEDULE_YEAR, kind=kind, code=self.district, name=self.district_name)
        return t("The Franklin County Auditor's {year} estimate of the {kind} for a typical Franklin County home.",
                 year=SCHEDULE_YEAR, kind=kind)


@dataclass
class HomesteadPlan:
    headline: str
    notes: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    caveats: list[str] = field(default_factory=lambda: [t(c) for c in CAVEATS])
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
    deadline = t(HOMESTEAD["deadline"])
    steps = []
    if a.gets_it_now == UNSURE:
        steps.append(Step(t("Check what the home gets now"),
                          t("Look the home up on the {search}. The tax section lists a 'Homestead' or 'Owner Occupancy' "
                            "credit if the home already gets one. Your tax bill shows them too.",
                            search=link("auditor_search")),
                          time=t("5 minutes online"), cost=t("Free"), where="auditor"))
    if VETERAN in a.qualifiers:
        steps.append(Step(t("Apply for the disabled veteran homestead exemption"),
                          t("The first {veteran} of the home's value isn't taxed, with no income limit. Fill out {form} "
                            "and include the VA letter showing a 100% rating.",
                            veteran=HOMESTEAD["veteran_value"], form=link("dte_105i")),
                          time=t("About 15 minutes"), cost=t("Free"), where="auditor"))
    if INCOME_TESTED & set(a.qualifiers) and qualifies and VETERAN not in a.qualifiers:
        steps.append(Step(t("Apply for the homestead exemption"),
                          t("The first {exempt} of the home's value isn't taxed. New applicants' income ({year} Ohio "
                            "modified adjusted gross income) must be {limit} or less. Fill out {form}; a disabled owner "
                            "also needs a doctor to sign the Certificate of Disability (DTE 105E). A surviving spouse "
                            "who already gets it may not need a new form; ask the Auditor.",
                            exempt=HOMESTEAD["exempt_value"], year=HOMESTEAD["income_year"],
                            limit=HOMESTEAD["income_limit"], form=link("dte_105a")),
                          time=t("About 15 minutes"), cost=t("Free"), where="auditor"))
    steps.append(Step(t("Apply for the owner occupancy credit"),
                      t("Any owner who lives in the home as their main home on January 1 can get it, with no age or "
                        "income limit. It lowers taxes from levies passed in November 2013 or earlier. Fill out "
                        "{form}. More: {info}.", form=link("dte_105c"), info=link("owner_occupancy")),
                      time=t("About 10 minutes"), cost=t("Free"), where="auditor"))
    steps.append(Step(t("File by {deadline}", deadline=deadline),
                      t("Apply by {deadline} of the year you want the tax break for. Late applications are accepted. "
                        "You don't reapply every year; the Auditor mails a renewal form each January.",
                        deadline=deadline),
                      time=t("Before the deadline"), cost=t("Free")))
    steps.append(Step(t("Ask the Auditor's office for help"),
                      t("{name}, {address}, {phone}. Details and the online form: {info}.",
                        name=name, address=address, phone=phone, info=link("homestead")),
                      time=t("One phone call"), cost=t("Free"), where="auditor"))
    return steps


def _report_changes() -> Step:
    return Step(t("Tell the Auditor when things change"),
                t("If the owner who got the tax break dies, sells or moves out, tell the Auditor. It doesn't pass to "
                  "heirs (only to a surviving spouse who qualifies), and tax breaks given to someone who no longer "
                  "qualifies may have to be paid back. {office}: {phone}.",
                  office=CONTACTS["auditor"][0], phone=CONTACTS["auditor"][2]),
                time=t("One phone call"), cost=t("Free"), where="auditor")


def _timeline(year: int) -> list[tuple[str, str]]:
    return [(t("By December 31, {year}", year=year),
             t("Send the application to the Auditor: online, by mail, or in person.")),
            (t("Early {year}", year=year + 1),
             t("The tax bill for {year} taxes (Ohio bills a year behind) should show the lower amount.", year=year)),
            (t("Every January after"),
             t("The Auditor mails a renewal form. Read it, and tell the Auditor if anything changed."))]


# ---------------------------------------------------------------- the decision
def homestead_plan(a: HomesteadAnswers, title_status: str, parcel_id: str = "", who: str = "the owner",
                   year: int | None = None) -> HomesteadPlan:
    """What a family can claim, given its answers, the title status from assess(), and the home's parcel number.

    `who` names the owners in plain words ("James and Louise") so the result can speak to this family. "you" means the
    person checking owns the home, and "the owner" means there are no names to use.
    """
    year = year or date.today().year
    veteran = VETERAN in a.qualifiers
    income_tested = bool(INCOME_TESTED & set(a.qualifiers))
    qualifies = veteran or (income_tested and a.income_ok != NO)
    savings = estimate(parcel_id, veteran) if qualifies else None

    if a.main_home == NO:
        steps = [_report_changes()] if a.gets_it_now != NO else []
        return HomesteadPlan(t("These tax breaks are only for the home an owner lives in"),
                             [t("The homestead exemption and the owner occupancy credit only go to an owner's main "
                                "home: where they lived on January 1, vote, and file income taxes.")],
                             steps + [Step(t("Check again if an owner moves in"),
                                           t("An owner who makes this their main home can apply for the next year."))])

    notes = []
    if income_tested and a.income_ok == NO and not veteran:
        notes.append(t("With income over {limit}, a new application for the homestead exemption won't qualify. One "
                       "exception: if it was already granted for 2013 at this home, the income limit doesn't apply. "
                       "The owner occupancy credit has no income limit.", limit=HOMESTEAD["income_limit"]))

    if title_status not in (PROTECTED, AT_RISK):
        notes.insert(0, t("The Auditor gives these tax breaks to owners on the County record who live in the home. If "
                          "the home is still in the name of someone who died, the family living there usually can't "
                          "apply until the title is in their name."))
        steps = [Step(t("Finish the title steps in your action plan first"),
                      t("Once the County record shows the right owner, come back to these steps."))]
        if a.gets_it_now != NO:
            steps.append(_report_changes())
        headline = (t("Finish the title filing, then apply") if title_status == IN_PROGRESS
                    else t("Clear the title first, then apply"))
        timeline = [(t("First"), t("Clear the title, so the County record shows who owns the home now.")),
                    (t("Then, by December 31"), t("The owner on the record applies for that year."))]
        return HomesteadPlan(headline, notes, steps + _apply_steps(a, qualifies), savings=savings, timeline=timeline)

    if a.gets_it_now == YES:
        notes.insert(0, t("Keep it: the renewal form comes each January."))
        steps = [_report_changes()]
        if a.qualifiers:
            steps.insert(0, Step(t("Make sure you get everything you qualify for"),
                                 t("Check the tax section on the {search} for both a 'Homestead' and an 'Owner "
                                   "Occupancy' credit. If one is missing, the Auditor can help: {phone}.",
                                   search=link("auditor_search"), phone=CONTACTS["auditor"][2]),
                                 time=t("5 minutes online"), cost=t("Free"), where="auditor"))
        return HomesteadPlan(t("The home already gets a homestead tax break"), notes, steps, savings=savings)

    if not a.qualifiers:
        notes.append(t("From your answers, the owner occupancy credit fits now. An owner can apply for the homestead "
                       "exemption in the year they turn 65 or become permanently disabled."))
    if savings and who == "you":
        headline = t("You could save about ${amount} a year", amount=f"{savings.yearly:,}")
    elif savings and who == "the owner":
        headline = t("The owner could save about ${amount} a year", amount=f"{savings.yearly:,}")
    elif savings:
        headline = t("{who} could save about ${amount} a year", who=who, amount=f"{savings.yearly:,}")
    else:
        headline = t("You may be able to lower your property taxes")
    return HomesteadPlan(headline, notes, _apply_steps(a, qualifies), savings=savings, timeline=_timeline(year))
