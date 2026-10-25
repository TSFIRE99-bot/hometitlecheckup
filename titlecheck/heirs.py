"""Who inherits a home when the owner dies with no will and nothing recorded (Ohio's 'statute of descent').

Based on Ohio Revised Code 2105.06 (who inherits, in order) and 2105.13 (a child who died before the owner is
represented by their own children, who split that child's share). Simplified on purpose: half-blood relatives,
adopted-out children, a will, and debts all change the answer. General information, not legal advice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from titlecheck.i18n import t


@dataclass
class Child:
    name: str
    living: bool = True
    grandchildren: int = 0          # living children of this child (only matter if this child has died)
    with_spouse: bool = True        # is the surviving spouse also this child's parent?


@dataclass
class Family:
    spouse_living: bool = False
    children: list[Child] = field(default_factory=list)
    parents_living: int = 0         # 0, 1 or 2
    siblings: int = 0               # living brothers and sisters (used only when there is no spouse, child or parent)


@dataclass
class Heir:
    name: str
    share: Fraction


@dataclass
class Inheritance:
    heirs: list[Heir]
    explanation: str
    law: str
    spouse_first_amount: int = 0    # dollars the spouse takes off the top before the shares are split

    @property
    def signers(self) -> int:
        """How many people would have to agree and sign to sell or refinance the home."""
        return len(self.heirs)


def _lines(family: Family) -> list[tuple[str, list[str]]]:
    """Each child's 'line': the child if living, or their children if the child has died. Empty lines drop out."""
    lines = []
    for c in family.children:
        if c.living:
            lines.append((c.name, [c.name]))
        elif c.grandchildren > 0:
            lines.append((c.name, [t("{name}'s child {n}", name=c.name, n=i + 1) for i in range(c.grandchildren)]))
    return lines


def _split(lines: list[tuple[str, list[str]]], total: Fraction) -> list[Heir]:
    """Equal share per line; inside a line the grandchildren split their parent's share equally (per stirpes)."""
    heirs = []
    each_line = total / len(lines)
    for _, people in lines:
        heirs += [Heir(p, each_line / len(people)) for p in people]
    return heirs


def who_inherits(family: Family) -> Inheritance:
    lines = _lines(family)
    spouse_name = t("Surviving spouse")
    if lines and family.spouse_living:
        line_children = [c for c in family.children if c.living or c.grandchildren > 0]
        spouse_is_parent = [c.with_spouse for c in line_children]
        if all(spouse_is_parent):
            return Inheritance([Heir(spouse_name, Fraction(1))],
                               t("When every child is also the surviving spouse's child, the spouse inherits "
                                 "everything."), "ORC 2105.06(B)")
        if len(lines) == 1:
            spouse, first, law = Fraction(1, 2), 20_000, "ORC 2105.06(C)"
            why = t("With a surviving spouse and one child who is not the spouse's child, the spouse first receives "
                    "${first} of the estate, then {share} of the rest. The child gets the remaining share.",
                    first=f"{first:,}", share=spouse)
        else:
            spouse, law = Fraction(1, 3), "ORC 2105.06(D)"
            first = 60_000 if any(spouse_is_parent) else 20_000
            if any(spouse_is_parent):
                why = t("With a surviving spouse and children who are not all the spouse's, the spouse first receives "
                        "${first} of the estate, then {share} of the rest. The children's lines split the remaining "
                        "share.", first=f"{first:,}", share=spouse)
            else:
                why = t("With a surviving spouse and children who are none of them the spouse's, the spouse first "
                        "receives ${first} of the estate, then {share} of the rest. The children's lines split the "
                        "remaining share.", first=f"{first:,}", share=spouse)
        return Inheritance([Heir(spouse_name, spouse)] + _split(lines, 1 - spouse), why, law, first)
    if lines:
        return Inheritance(_split(lines, Fraction(1)),
                           t("With no surviving spouse, the children inherit equally. If a child has died, that "
                             "child's own children split their parent's share."), "ORC 2105.06(A), 2105.13")
    if family.spouse_living:
        return Inheritance([Heir(spouse_name, Fraction(1))],
                           t("With no children or grandchildren, the surviving spouse inherits everything."),
                           "ORC 2105.06(E)")
    if family.parents_living:
        n = family.parents_living
        return Inheritance([Heir(t("Parent {n}", n=i + 1) if n > 1 else t("Parent"), Fraction(1, n)) for i in range(n)],
                           t("With no spouse, children or grandchildren, the parents inherit equally."),
                           "ORC 2105.06(F)")
    if family.siblings:
        n = family.siblings
        return Inheritance([Heir(t("Brother or sister {n}", n=i + 1), Fraction(1, n)) for i in range(n)],
                           t("With no spouse, children, grandchildren or parents, the brothers and sisters inherit "
                             "equally (their children step in for any who have died)."), "ORC 2105.06(G)")
    return Inheritance([], t("More distant relatives (grandparents, aunts, uncles, cousins) inherit next. This one "
                             "needs a lawyer to sort out."), "ORC 2105.06(H)-(J)")


def share_values(result: Inheritance, home_value: int) -> list[int]:
    """What each heir's share of the home is worth in dollars, rounded, in the same order as result.heirs.

    The spouse's dollar amount 'off the top' comes out of the whole estate, not just the home, so it isn't counted here.
    """
    return [round(home_value * h.share) for h in result.heirs]


def frozen_equity(result: Inheritance, home_value: int) -> int:
    """Dollars that can't be sold, refinanced or borrowed against until every heir signs (all of it, if 2+ heirs)."""
    return home_value if result.signers > 1 else 0


def generations(children_each: int, count: int) -> list[tuple[int, int]]:
    """If nothing is ever filed: (generation, number of owners) when each owner leaves `children_each` heirs."""
    return [(g, max(1, children_each) ** g) for g in range(count + 1)]
