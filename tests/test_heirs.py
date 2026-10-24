from fractions import Fraction

from titlecheck.heirs import Child, Family, generations, who_inherits


def shares(family):
    return {h.name: h.share for h in who_inherits(family).heirs}


def test_children_split_equally_without_a_spouse():
    assert shares(Family(children=[Child("Ana"), Child("Ben")])) == {"Ana": Fraction(1, 2), "Ben": Fraction(1, 2)}


def test_grandchildren_split_their_parents_share():
    got = shares(Family(children=[Child("Ana"), Child("Ben", living=False, grandchildren=2)]))
    assert got == {"Ana": Fraction(1, 2), "Ben's child 1": Fraction(1, 4), "Ben's child 2": Fraction(1, 4)}
    assert sum(got.values()) == 1


def test_child_who_died_with_no_children_drops_out():
    assert shares(Family(children=[Child("Ana"), Child("Ben", living=False)])) == {"Ana": Fraction(1)}


def test_spouse_takes_all_when_every_child_is_theirs():
    assert shares(Family(spouse_living=True, children=[Child("Ana"), Child("Ben")])) == {"Surviving spouse": 1}


def test_spouse_and_one_child_from_another_relationship():
    r = who_inherits(Family(spouse_living=True, children=[Child("Ana", with_spouse=False)]))
    assert {h.name: h.share for h in r.heirs} == {"Surviving spouse": Fraction(1, 2), "Ana": Fraction(1, 2)}
    assert r.spouse_first_amount == 20_000 and r.law == "ORC 2105.06(C)"


def test_spouse_and_mixed_children():
    r = who_inherits(Family(spouse_living=True, children=[Child("Ana"), Child("Ben", with_spouse=False)]))
    got = {h.name: h.share for h in r.heirs}
    assert got["Surviving spouse"] == Fraction(1, 3) and got["Ana"] == got["Ben"] == Fraction(1, 3)
    assert r.spouse_first_amount == 60_000 and r.signers == 3


def test_spouse_is_parent_of_none():
    r = who_inherits(Family(spouse_living=True, children=[Child("A", with_spouse=False), Child("B", with_spouse=False)]))
    assert r.spouse_first_amount == 20_000


def test_no_children():
    assert shares(Family(spouse_living=True)) == {"Surviving spouse": 1}
    assert shares(Family(parents_living=2)) == {"Parent 1": Fraction(1, 2), "Parent 2": Fraction(1, 2)}
    assert len(shares(Family(siblings=3))) == 3
    assert who_inherits(Family()).heirs == []


def test_generations():
    assert generations(3, 3) == [(0, 1), (1, 3), (2, 9), (3, 27)]
