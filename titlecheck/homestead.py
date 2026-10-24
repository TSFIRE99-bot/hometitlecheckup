"""Optional Homestead Benefits Check: which Ohio property tax breaks a family might claim, and how, in Franklin County.

Shown after the title result. The homestead exemption and the owner occupancy credit go to owners on the County record
who live in the home, so a title that isn't settled comes first. Only the County Auditor decides who qualifies.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from titlecheck.assess import AT_RISK, IN_PROGRESS, NO, PROTECTED, UNSURE, YES, Step
from titlecheck.resources import CONTACTS, HOMESTEAD, link

SENIOR = "65 or older (or turning 65 this year)"
DISABLED = "Permanently and totally disabled"
SPOUSE = "Surviving spouse of someone who got the exemption (59 or older when they died)"
VETERAN = "Veteran with a 100% service-connected disability rating, or their surviving spouse"
QUALIFIERS = [SENIOR, DISABLED, SPOUSE, VETERAN]

EXPLAINER = (f"Ohio's **homestead exemption** lowers property taxes for homeowners who are 65 or older, permanently "
             f"disabled, or a qualifying surviving spouse: the first {HOMESTEAD['exempt_value']} of the home's value "
             f"isn't taxed ({HOMESTEAD['veteran_value']} for veterans with a 100% disability rating). Any owner who "
             "lives in the home can also get a smaller **owner occupancy credit**. Both are free to apply for, through "
             "the Franklin County Auditor.")

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


@dataclass
class HomesteadPlan:
    headline: str
    notes: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    caveats: list[str] = field(default_factory=lambda: list(CAVEATS))


# ---------------------------------------------------------------- plan building blocks
def _apply_steps(a: HomesteadAnswers) -> list[Step]:
    name, address, phone = CONTACTS["auditor"]
    steps = []
    if a.gets_it_now == UNSURE:
        steps.append(Step("Check what the home gets now",
                          f"Look the home up on the {link('auditor_search')}. The tax section lists a 'Homestead' "
                          "or 'Owner Occupancy' credit if the home already gets one. Your tax bill shows them too."))
    if VETERAN in a.qualifiers:
        steps.append(Step("Apply for the disabled veteran homestead exemption",
                          f"The first {HOMESTEAD['veteran_value']} of the home's value isn't taxed, with no income "
                          f"limit. Fill out {link('dte_105i')} and include the VA letter showing a 100% rating."))
    if {SENIOR, DISABLED, SPOUSE} & set(a.qualifiers):
        steps.append(Step("Apply for the homestead exemption",
                          f"The first {HOMESTEAD['exempt_value']} of the home's value isn't taxed. New applicants' "
                          f"income ({HOMESTEAD['income_year']} Ohio modified adjusted gross income) must be "
                          f"{HOMESTEAD['income_limit']} or less. Fill out {link('dte_105a')}; a disabled owner also "
                          "needs a doctor to sign the Certificate of Disability (DTE 105E). A surviving spouse who "
                          "already gets it may not need a new form; ask the Auditor."))
    steps.append(Step("Apply for the owner occupancy credit",
                      "Any owner who lives in the home as their main home on January 1 can get it, with no age or "
                      f"income limit. It lowers taxes from levies passed in November 2013 or earlier. Fill out "
                      f"{link('dte_105c')}. More: {link('owner_occupancy')}."))
    steps.append(Step(f"File by {HOMESTEAD['deadline']}",
                      f"Apply by {HOMESTEAD['deadline']} of the year you want the tax break for. Late applications are "
                      "accepted. You don't reapply every year; the Auditor mails a renewal form each January."))
    steps.append(Step("Ask the Auditor's office for help",
                      f"{name}, {address}, {phone}. Details and the online form: {link('homestead')}."))
    return steps


def _report_changes() -> Step:
    return Step("Tell the Auditor when things change",
                "If the owner who got the tax break dies, sells or moves out, tell the Auditor. It doesn't pass to "
                "heirs (only to a surviving spouse who qualifies), and tax breaks given to someone who no longer "
                f"qualifies may have to be paid back. {CONTACTS['auditor'][0]}: {CONTACTS['auditor'][2]}.")


# ---------------------------------------------------------------- the decision
def homestead_plan(a: HomesteadAnswers, title_status: str) -> HomesteadPlan:
    """What a family can claim, given its answers and the title status from assess()."""
    if a.main_home == NO:
        steps = [_report_changes()] if a.gets_it_now != NO else []
        return HomesteadPlan("These tax breaks are only for the home an owner lives in",
                             ["The homestead exemption and the owner occupancy credit only go to an owner's main home: "
                              "where they lived on January 1, vote, and file income taxes."],
                             steps + [Step("Check again if an owner moves in",
                                           "An owner who makes this their main home can apply for the next year.")])

    if title_status not in (PROTECTED, AT_RISK):
        notes = ["The Auditor gives these tax breaks to owners on the County record who live in the home. If the home "
                 "is still in the name of someone who died, the family living there usually can't apply until the "
                 "title is in their name."]
        steps = [Step("Finish the title steps in your action plan first",
                      "Once the County record shows the right owner, come back to these steps.")]
        if a.gets_it_now != NO:
            steps.append(_report_changes())
        headline = ("Finish the title filing, then apply" if title_status == IN_PROGRESS
                    else "Clear the title first, then apply")
        return HomesteadPlan(headline, notes, steps + _apply_steps(a))

    if a.gets_it_now == YES:
        notes = ["Keep it: the renewal form comes each January."]
        steps = [_report_changes()]
        if a.qualifiers:
            steps.insert(0, Step("Make sure you get everything you qualify for",
                                 f"Check the tax section on the {link('auditor_search')} for both a 'Homestead' and "
                                 f"an 'Owner Occupancy' credit. If one is missing, the Auditor can help: "
                                 f"{CONTACTS['auditor'][2]}."))
        return HomesteadPlan("The home already gets a homestead tax break", notes, steps)

    notes = []
    if not a.qualifiers:
        notes.append("From your answers, the owner occupancy credit fits now. An owner can apply for the homestead "
                     "exemption in the year they turn 65 or become permanently disabled.")
    return HomesteadPlan("You may be able to lower your property taxes", notes, _apply_steps(a))
