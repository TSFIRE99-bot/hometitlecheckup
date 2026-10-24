"""The checkup screen's questions, built from the submitted form.

The web app keeps nothing on the server between clicks. Once a home is found, its public record (address, owners,
years since it changed hands) rides along in hidden form fields, and every answer comes back with each click. These
functions turn that form into the same Answers the decision rules in titlecheck/assess.py use.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from titlecheck.assess import ESTATE_SIZES, NO, UNSURE, YES, Answers, owner_kind, pretty
from titlecheck.homestead import QUALIFIERS, HomesteadAnswers

CHOICES = [YES, NO, UNSURE]


@dataclass
class Question:
    key: str
    label: str                  # may use **bold**
    help: str | None = None
    choices: list[str] = field(default_factory=lambda: list(CHOICES))
    value: str | None = None    # what was picked, if anything
    multi: bool = False         # checkboxes instead of one choice
    values: list[str] = field(default_factory=list)


class Form:
    """Collects the questions asked, reading each answer from the submitted form (a dict-like with getlist)."""

    def __init__(self, data):
        self.data = data
        self.questions: list[Question] = []

    def ask(self, key: str, label: str, help_text: str | None = None, choices: list[str] | None = None) -> str:
        choices = choices or list(CHOICES)
        value = self.data.get(key)
        value = value if value in choices else None
        self.questions.append(Question(key, label, help_text, choices, value))
        return value or UNSURE

    def pick_many(self, key: str, label: str, choices: list[str]) -> list[str]:
        values = [v for v in self.data.getlist(key) if v in choices]
        self.questions.append(Question(key, label, None, choices, multi=True, values=values))
        return values


def title_questions(owners: list[str], data) -> tuple[list[Question], Answers]:
    """Step 2: the same questions, in the same order, as the original Streamlit screen."""
    f = Form(data)
    people = [o for o in owners if owner_kind(o) == "person"]
    kinds = {owner_kind(o) for o in owners}
    alive = {p: f.ask(f"alive_{i}", f"Is **{pretty(p)}** living?") for i, p in enumerate(people)}
    a = Answers(owners_alive=alive)
    someone_died = NO in alive.values() or "estate" in kinds

    if people and all(v == YES for v in alive.values()) and "estate" not in kinds:
        a.tod_recorded = f.ask("q_tod", "Has a **Transfer on Death affidavit** been recorded for this home?",
                               "A one-page form, recorded with the County, that names who gets the home next.")
    elif someone_died:
        living = [p for p, v in alive.items() if v == YES]
        if living and len(people) >= 2:
            a.survivorship = f.ask("q_surv", "Does the deed say **'with right of survivorship'**?",
                                   "It means the living owner automatically keeps the home.")
        a.tod_recorded = f.ask("q_tod", "Before the death, was a **Transfer on Death affidavit** recorded?",
                               "A one-page form, recorded with the County, that names who gets the home next.")
        a.probate_opened = f.ask("q_probate", "Has a **probate case** been opened in court?")
        if a.tod_recorded != YES and a.probate_opened != YES and a.survivorship != YES:
            a.spouse_gets_all = f.ask("q_spouse", "Is a **surviving spouse** inheriting everything?",
                                      "This helps find the simplest court process.")
            a.estate_size = f.ask("q_size", "Roughly how much was **everything they left** worth, house included?",
                                  choices=ESTATE_SIZES)
            a.only_real_estate = f.ask("q_only", "Did they leave **only the house** (no bank accounts, cars, or "
                                       "other property)?")
    return f.questions, a


def homestead_questions(data) -> tuple[list[Question], HomesteadAnswers]:
    f = Form(data)
    h = HomesteadAnswers(main_home=f.ask("q_hs_main", "Does an owner **live in this home as their main home**?",
                                         "Where they lived on January 1, are registered to vote, and file taxes."))
    if h.main_home != NO:
        h.gets_it_now = f.ask("q_hs_now", "Does the home **get the homestead exemption now**?",
                              "It shows on the tax bill and the Auditor's website as a 'Homestead' credit.")
        h.qualifiers = f.pick_many("q_hs_who", "Do any of these fit an owner who lives here? Pick all that apply, "
                                   "or none.", QUALIFIERS)
    return f.questions, h
