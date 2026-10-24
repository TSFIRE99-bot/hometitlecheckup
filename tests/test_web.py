import pytest
from werkzeug.datastructures import MultiDict

from app import app
from titlecheck.assess import NO, YES
from titlecheck.demo import DEMO
from titlecheck.lookup import AddressLookupError, Parcel
from web import routes
from web.markup import md


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def demo_record(**answers):
    """The hidden fields the demo home's answer form sends, plus answers."""
    data = MultiDict([("pid", "DEMO"), ("addr", DEMO.address), ("years", "38"), ("year", "1987"), ("lot", "0.16 acres")]
                     + [("owners", o) for o in DEMO.owners])
    for k, v in answers.items():
        data.setlist(k, v if isinstance(v, list) else [v])
    return data


@pytest.mark.parametrize("path", ["/", "/inherit", "/learn", "/about", "/help"])
def test_every_page_loads(client, path):
    r = client.get(path)
    assert r.status_code == 200 and b"Home Title Checkup" in r.data


def test_stylesheet_and_script_are_served(client):
    assert client.get("/style.css").status_code == 200
    assert client.get("/app.js").status_code == 200


def test_demo_home_shows_record_map_and_questions(client):
    html = client.post("/", data={"action": "demo"}).get_data(as_text=True)
    assert "1234 SAMPLE ST (demo home, not real)" in html
    assert "James L Parker" in html and "Louise M Parker" in html
    assert "<iframe" in html and "Neighbor: Right" in html
    assert "World_Imagery" not in html            # the made-up block never sits on a real satellite photo
    assert 'name="alive_0"' in html and "Homestead Benefits Check" in html


def test_answers_update_without_the_map(client):
    r = client.post("/", data=demo_record(alive_0=YES, alive_1=YES, q_tod=NO), headers={"X-Partial": "1"})
    html = r.get_data(as_text=True)
    assert "Not protected yet" in html and "Transfer on Death" in html
    assert "<iframe" not in html and "<html" not in html


def test_someone_died_nothing_filed_is_tangled(client):
    data = demo_record(alive_0=NO, alive_1=NO, q_tod=NO, q_probate=NO, q_size="Over $100,000")
    html = client.post("/", data=data, headers={"X-Partial": "1"}).get_data(as_text=True)
    assert "Likely tangled title" in html and "Open a probate case" in html


def test_homestead_section_follows_the_title_status(client):
    data = demo_record(alive_0=NO, alive_1=NO, q_tod=NO, q_probate=NO, q_hs_main=YES)
    html = client.post("/", data=data, headers={"X-Partial": "1"}).get_data(as_text=True)
    assert "Clear the title first, then apply" in html
    assert 'id="homestead" open' in html
    assert "automatically get you the exemption" in html


def test_result_speaks_to_the_person_checking(client):
    data = demo_record(alive_0=YES, alive_1=YES, q_tod=NO, you="Maria", role="A family member's home")
    html = client.post("/", data=data, headers={"X-Partial": "1"}).get_data(as_text=True)
    assert "Maria, here&#39;s your plan" in html
    assert "James and Louise still own the home" in html


def test_owner_hears_about_their_own_home(client):
    data = demo_record(alive_0=YES, alive_1=YES, q_tod=NO, role="My own home")
    html = client.post("/", data=data, headers={"X-Partial": "1"}).get_data(as_text=True)
    assert "Here&#39;s your plan" in html and "safely in your name" in html


def test_typed_first_name_is_cleaned(client):
    data = demo_record(you="<b>Maria</b>")
    html = client.post("/", data=data, headers={"X-Partial": "1"}).get_data(as_text=True)
    assert "<b>Maria" not in html


def test_roadmap_shows_time_cost_and_where_to_go(client):
    html = client.post("/", data=demo_record(alive_0=YES, alive_1=YES, q_tod=NO),
                       headers={"X-Partial": "1"}).get_data(as_text=True)
    assert 'data-roadmap="DEMO|' in html and 'data-step="0"' in html
    assert "$34 recording fee" in html and 'href="/help#recorder"' in html


def test_homestead_questions_use_the_owners_names(client):
    data = demo_record(q_hs_main=YES, q_hs_who=["65 or older (or turning 65 this year)"])
    html = client.post("/", data=data, headers={"X-Partial": "1"}).get_data(as_text=True)
    assert "James or Louise" in html and 'name="q_hs_income"' in html


def test_homestead_savings_show_for_a_qualifying_owner(client):
    data = demo_record(alive_0=YES, alive_1=YES, q_tod=YES, q_hs_main=YES, q_hs_now=NO, q_hs_income=YES,
                       q_hs_who=["65 or older (or turning 65 this year)"])
    html = client.post("/", data=data, headers={"X-Partial": "1"}).get_data(as_text=True)
    assert "James and Louise could save about $" in html and "estimated savings a year" in html


def test_help_page_lists_the_free_offices(client):
    html = client.get("/help").get_data(as_text=True)
    assert "Legal Aid of Southeast and Central Ohio" in html and "(888) 246-4420" in html
    assert "373 S. High St., 18th floor" in html and 'id="probate"' in html and "<iframe" in html


def test_plan_pdf_downloads(client):
    r = client.post("/plan.pdf", data=demo_record(alive_0=YES, alive_1=YES, q_tod=NO, you="Maria"))
    assert r.mimetype == "application/pdf" and r.data[:4] == b"%PDF"
    assert "attachment" in r.headers["Content-Disposition"]


def test_homestead_pdf_downloads(client):
    r = client.post("/homestead.pdf", data=demo_record(q_hs_main=YES, q_hs_now=NO,
                                                       q_hs_who=["65 or older (or turning 65 this year)"]))
    assert r.mimetype == "application/pdf" and r.data[:4] == b"%PDF"


def test_pdf_without_a_home_is_refused(client):
    assert client.post("/plan.pdf", data={}).status_code == 400


def test_lookup_error_offers_typing_the_names(client, monkeypatch):
    def fail(_):
        raise AddressLookupError("Couldn't reach the County's property records right now.")
    monkeypatch.setattr(routes, "find_parcels", fail)
    html = client.post("/", data={"action": "lookup", "address": "123 Main St"}).get_data(as_text=True)
    assert "Couldn't reach the County" in html and 'name="names"' in html


def test_several_matches_ask_which_one(client, monkeypatch):
    homes = [Parcel(f"010-00000{i}", f"12{i} MAIN ST", "43215", ["DOE JANE"], None, "") for i in range(2)]
    monkeypatch.setattr(routes, "find_parcels", lambda _: homes)
    html = client.post("/", data={"action": "lookup", "address": "12 Main St"}).get_data(as_text=True)
    assert "Which one?" in html and 'value="010-000001"' in html
    html = client.post("/", data={"action": "pick", "address": "12 Main St", "pick": "010-000001"}).get_data(as_text=True)
    assert "121 MAIN ST" in html and "Jane Doe" in html


def test_typed_names_work_without_the_county(client):
    html = client.post("/", data={"action": "manual", "names": "Louise Parker\nJames Parker"}).get_data(as_text=True)
    assert "Louise Parker" in html and 'name="alive_1"' in html and "no map" in html


def test_typed_names_are_never_turned_into_html(client):
    html = client.post("/", data={"action": "manual", "names": "<script>alert(1)</script>"}).get_data(as_text=True)
    assert "<SCRIPT>ALERT" not in html.upper() and "&lt;" in html


def test_markup_keeps_bold_and_links_but_escapes_html():
    assert str(md("**Hi** [Site](https://example.org) <b>")) == (
        '<strong>Hi</strong> <a href="https://example.org" target="_blank" rel="noopener">Site</a> &lt;b&gt;')


def test_inherit_defaults_and_spouse(client):
    html = client.get("/inherit").get_data(as_text=True)
    assert "2 people would own the home" in html
    html = client.post("/inherit", data={"spouse": "on", "count": "2", "name_0": "Ann", "living_0": "on",
                                         "name_1": "Ben", "living_1": "on"}, headers={"X-Partial": "1"}).get_data(as_text=True)
    assert "1 person owns the home" in html          # first time the spouse box is ticked, children count as theirs


def test_inherit_child_who_died_is_replaced_by_their_children(client):
    data = {"count": "2", "name_0": "Ann", "living_0": "on", "name_1": "Ben", "gk_1": "2"}
    html = client.post("/inherit", data=data, headers={"X-Partial": "1"}).get_data(as_text=True)
    assert "3 people would own the home" in html and "Ben&#39;s child 1" in html
