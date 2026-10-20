import pytest

from titlecheck.assess import (AT_RISK, CHECK, IN_PROGRESS, NO, PROTECTED, TANGLED, UNSURE, YES, Answers, assess,
                               owner_kind, record_notes)
from titlecheck.checklist import build_pdf

A, B = "PARKER JAMES L", "PARKER LOUISE M"


def run(owners, **kw):
    alive = kw.pop("alive")
    return assess(owners, Answers(owners_alive=dict(zip([o for o in owners if owner_kind(o) == "person"], alive)), **kw))


@pytest.mark.parametrize("name, kind", [
    ("SMITH TRACY L", "person"), ("TRAN MINH", "person"), ("JONES MARY TR", "trust"),
    ("SMITH FAMILY TRUST", "trust"), ("BROWN ANN TTEE", "trust"), ("DOE JOHN ESTATE", "estate"),
    ("ABC HOLDINGS LLC", "organization"), ("FRANKLIN COUNTY COMM", "organization"),
])
def test_owner_kind(name, kind):
    assert owner_kind(name) == kind


def test_everyone_alive_no_tod_is_at_risk():
    r = run([A, B], alive=[YES, YES], tod_recorded=NO)
    assert r.status == AT_RISK
    assert any("Transfer on Death" in s.title for s in r.steps)


def test_everyone_alive_with_tod_is_protected():
    assert run([A], alive=[YES], tod_recorded=YES).status == PROTECTED


def test_unsure_if_alive_asks_to_check():
    assert run([A], alive=[UNSURE]).status == CHECK


def test_sole_owner_died_nothing_filed_is_tangled():
    r = run([A], alive=[NO], tod_recorded=NO, probate_opened=NO, estate_size="Over $100,000")
    assert r.status == TANGLED
    assert any("probate case" in s.title.lower() for s in r.steps)


def test_small_estate_gets_release_from_administration():
    r = run([A], alive=[NO], tod_recorded=NO, probate_opened=NO, estate_size="Under $35,000")
    assert "Release from Administration" in r.steps[0].title


def test_spouse_up_to_100k_gets_release_from_administration():
    r = run([A, B], alive=[NO, NO], tod_recorded=NO, probate_opened=NO, estate_size="$35,000 to $100,000",
            spouse_gets_all=YES)
    assert "Release from Administration" in r.steps[0].title


def test_real_estate_only_option():
    r = run([A], alive=[NO], tod_recorded=NO, probate_opened=NO, estate_size="Over $100,000", only_real_estate=YES)
    assert "Real Estate Transfer Only" in r.steps[0].title


def test_survivorship_deed_is_in_progress():
    r = run([A, B], alive=[NO, YES], survivorship=YES, tod_recorded=NO)
    assert r.status == IN_PROGRESS
    assert "survivorship" in r.steps[0].title.lower()


def test_tod_recorded_before_death_is_in_progress():
    r = run([A], alive=[NO], tod_recorded=YES)
    assert r.status == IN_PROGRESS
    assert "confirmation" in r.steps[0].title.lower()


def test_unknown_filings_after_death_says_check_recorder():
    assert run([A], alive=[NO], tod_recorded=UNSURE, probate_opened=NO).status == CHECK


def test_estate_owner_without_probate_is_tangled():
    assert run(["PARKER JAMES L ESTATE"], alive=[], probate_opened=NO).status == TANGLED


def test_estate_owner_with_probate_is_in_progress():
    assert run(["PARKER JAMES L ESTATE"], alive=[], probate_opened=YES).status == IN_PROGRESS


def test_trust_is_protected():
    assert run(["PARKER FAMILY TRUST"], alive=[]).status == PROTECTED


def test_company_is_out_of_scope():
    assert run(["ABC HOLDINGS LLC"], alive=[]).status == CHECK


def test_every_plan_ends_with_free_legal_help():
    for kw in [dict(alive=[YES], tod_recorded=NO), dict(alive=[NO], tod_recorded=NO, probate_opened=NO),
               dict(alive=[NO], tod_recorded=YES), dict(alive=[UNSURE])]:
        assert run([A], **kw).steps[-1].title == "Get free legal help"


def test_record_notes():
    notes = record_notes([A, B], 38)
    assert any("38 years" in n for n in notes) and any("2 owners" in n for n in notes)
    assert any("estate" in n for n in record_notes(["DOE JOHN ESTATE"], None))


def test_pdf_builds():
    r = run([A], alive=[NO], tod_recorded=NO, probate_opened=NO, estate_size="Under $35,000")
    pdf = build_pdf(r, "1234 SAMPLE ST", record_notes([A], 38))
    assert pdf[:4] == b"%PDF" and len(pdf) > 1000
