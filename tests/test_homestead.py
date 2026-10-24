from titlecheck.assess import AT_RISK, IN_PROGRESS, NO, PROTECTED, TANGLED, UNSURE, YES
from titlecheck.checklist import build_homestead_pdf
from titlecheck.homestead import DISABLED, SENIOR, SPOUSE, VETERAN, HomesteadAnswers, homestead_plan


def titles(plan):
    return [s.title for s in plan.steps]


def test_not_main_home_gets_no_tax_break():
    p = homestead_plan(HomesteadAnswers(main_home=NO, gets_it_now=NO), PROTECTED)
    assert "only for the home" in p.headline
    assert not any("Apply" in t for t in titles(p))


def test_not_main_home_but_getting_it_says_tell_the_auditor():
    p = homestead_plan(HomesteadAnswers(main_home=NO, gets_it_now=YES), PROTECTED)
    assert "Tell the Auditor when things change" in titles(p)


def test_senior_on_clear_title_applies_for_homestead_and_owner_occupancy():
    p = homestead_plan(HomesteadAnswers(main_home=YES, gets_it_now=NO, qualifiers=[SENIOR]), AT_RISK)
    assert "Apply for the homestead exemption" in titles(p)
    assert "Apply for the owner occupancy credit" in titles(p)
    assert any("DTE 105A" in s.detail for s in p.steps)


def test_disabled_and_surviving_spouse_use_the_same_form():
    for q in (DISABLED, SPOUSE):
        p = homestead_plan(HomesteadAnswers(main_home=YES, gets_it_now=NO, qualifiers=[q]), PROTECTED)
        assert "Apply for the homestead exemption" in titles(p)


def test_veteran_gets_the_veteran_form():
    p = homestead_plan(HomesteadAnswers(main_home=YES, gets_it_now=NO, qualifiers=[VETERAN]), PROTECTED)
    assert "Apply for the disabled veteran homestead exemption" in titles(p)
    assert "Apply for the homestead exemption" not in titles(p)


def test_no_qualifiers_still_gets_owner_occupancy_credit():
    p = homestead_plan(HomesteadAnswers(main_home=YES, gets_it_now=NO), PROTECTED)
    assert "Apply for the owner occupancy credit" in titles(p)
    assert "Apply for the homestead exemption" not in titles(p)
    assert any("turn 65" in n for n in p.notes)


def test_unsure_if_getting_it_says_check_first():
    p = homestead_plan(HomesteadAnswers(main_home=YES, gets_it_now=UNSURE), PROTECTED)
    assert titles(p)[0] == "Check what the home gets now"


def test_already_getting_it_keeps_it():
    p = homestead_plan(HomesteadAnswers(main_home=YES, gets_it_now=YES, qualifiers=[SENIOR]), PROTECTED)
    assert "already gets" in p.headline
    assert titles(p)[-1] == "Tell the Auditor when things change"


def test_tangled_title_comes_first():
    p = homestead_plan(HomesteadAnswers(main_home=YES, gets_it_now=UNSURE, qualifiers=[SENIOR]), TANGLED)
    assert p.headline == "Clear the title first, then apply"
    assert titles(p)[0] == "Finish the title steps in your action plan first"
    assert "Tell the Auditor when things change" in titles(p)


def test_title_in_progress_finishes_filing_first():
    p = homestead_plan(HomesteadAnswers(main_home=YES, gets_it_now=NO), IN_PROGRESS)
    assert p.headline == "Finish the title filing, then apply"
    assert "Tell the Auditor when things change" not in titles(p)


def test_every_plan_says_the_auditor_decides_and_a_clear_title_is_not_a_guarantee():
    for status in (PROTECTED, AT_RISK, TANGLED, IN_PROGRESS):
        for main in (YES, NO, UNSURE):
            caveats = " ".join(homestead_plan(HomesteadAnswers(main_home=main), status).caveats)
            assert "Only the Franklin County Auditor can approve it" in caveats
            assert "doesn't automatically get you the exemption" in caveats


def test_homestead_pdf_builds():
    p = homestead_plan(HomesteadAnswers(main_home=YES, gets_it_now=NO, qualifiers=[SENIOR, VETERAN]), PROTECTED)
    pdf = build_homestead_pdf(p, "1234 SAMPLE ST")
    assert pdf[:4] == b"%PDF" and len(pdf) > 1000
