import pytest
from werkzeug.datastructures import MultiDict

from app import app
from titlecheck import i18n
from titlecheck.demo import DEMO
from titlecheck.locale import es, so

SENIOR = "65 or older (or turning 65 this year)"
VETERAN = "Veteran with a 100% service-connected disability rating, or their surviving spouse"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def demo(**answers):
    data = MultiDict([("pid", "DEMO"), ("addr", DEMO.address), ("years", "38"), ("year", "1987"), ("lot", "0.16 acres")]
                     + [("owners", o) for o in DEMO.owners])
    for k, v in answers.items():
        data.setlist(k, v if isinstance(v, list) else [v])
    return data


# Answer combinations that reach every result, step and homestead branch
FLOWS = [
    dict(alive_0="Yes", alive_1="Yes", q_tod="No", role="My own home", you="Ana"),
    dict(alive_0="Yes", alive_1="Yes", q_tod="Yes", role="Someone I'm helping"),
    dict(alive_0="Yes", alive_1="Yes", q_tod="Not sure"),
    dict(alive_0="Not sure", alive_1="Yes"),
    dict(alive_0="No", alive_1="Yes", q_surv="Yes", q_tod="No"),
    dict(alive_0="No", alive_1="No", q_tod="Yes"),
    dict(alive_0="No", alive_1="No", q_tod="No", q_probate="Yes"),
    dict(alive_0="No", alive_1="No", q_tod="Not sure", q_probate="No"),
    dict(alive_0="No", alive_1="No", q_tod="No", q_probate="No", q_size="Under $35,000"),
    dict(alive_0="No", alive_1="No", q_tod="No", q_probate="No", q_size="Over $100,000", q_only="Yes"),
    dict(alive_0="No", alive_1="No", q_tod="No", q_probate="No", q_size="Over $100,000", q_only="No",
         q_hs_main="Yes", q_hs_now="Yes"),
    dict(alive_0="Yes", alive_1="Yes", q_tod="No", q_hs_main="Yes", q_hs_now="No", q_hs_who=[SENIOR], q_hs_income="Yes"),
    dict(alive_0="Yes", alive_1="Yes", q_tod="No", q_hs_main="Yes", q_hs_now="Not sure", q_hs_who=[SENIOR],
         q_hs_income="No"),
    dict(alive_0="Yes", alive_1="Yes", q_tod="No", q_hs_main="Yes", q_hs_now="No", q_hs_who=[VETERAN]),
    dict(alive_0="Yes", alive_1="Yes", q_tod="No", q_hs_main="Yes", q_hs_now="Yes", q_hs_who=[SENIOR]),
    dict(alive_0="Yes", alive_1="Yes", q_tod="No", q_hs_main="No", q_hs_now="Yes"),
    dict(alive_0="Yes", alive_1="Yes", q_tod="No", q_hs_main="Yes", q_hs_now="No"),
]


def test_both_catalogs_translate_the_same_sentences():
    assert set(es.T) == set(so.T) and len(es.T) > 400


@pytest.mark.parametrize("lang", ["es", "so"])
def test_every_page_and_flow_is_fully_translated(client, lang):
    i18n.MISSING.clear()
    client.set_cookie("lang", lang)
    for path in ["/", "/inherit", "/learn", "/about", "/help"]:
        assert client.get(path).status_code == 200
    assert client.post("/", data={"action": "demo"}).status_code == 200
    for flow in FLOWS:
        assert client.post("/", data=demo(**flow), headers={"X-Partial": "1"}).status_code == 200
        assert client.post("/plan.pdf", data=demo(**flow)).data[:4] == b"%PDF"
        assert client.post("/homestead.pdf", data=demo(**flow)).data[:4] == b"%PDF"
    assert client.post("/", data={"action": "manual", "names": "Ana Diaz"}).status_code == 200
    assert client.post("/", data={"action": "lookup", "address": ""}).status_code == 200
    for family in [{"spouse": "on", "count": "1", "name_0": "A", "living_0": "on", "spouse_was": "on"},
                   {"spouse": "on", "count": "2", "name_0": "A", "living_0": "on", "name_1": "B", "living_1": "on",
                    "spouse_was": "on", "ws_0": "on"},
                   {"spouse": "on", "count": "2", "name_0": "A", "living_0": "on", "name_1": "B", "living_1": "on",
                    "spouse_was": "on"},
                   {"count": "2", "name_0": "A", "living_0": "on", "name_1": "B", "gk_1": "2", "value": ""},
                   {"count": "0", "parents": "2"}, {"count": "0", "siblings": "3"}, {"count": "0"},
                   {"spouse": "on", "count": "0"}]:
        assert client.post("/inherit", data=family, headers={"X-Partial": "1"}).status_code == 200
    assert not {text for code, text in i18n.MISSING if code == lang}


def test_spanish_page_is_in_spanish(client):
    client.set_cookie("lang", "es")
    html = client.post("/", data=demo(alive_0="Yes", alive_1="Yes", q_tod="No"),
                       headers={"X-Partial": "1"}).get_data(as_text=True)
    assert "Todavía no está protegida" in html and "James y Louise" in html and "Not protected yet" not in html


def test_somali_page_is_in_somali(client):
    html = client.get("/?lang=so").get_data(as_text=True)
    assert 'lang="so"' in html and "Hubi gurigan" in html


def test_choosing_a_language_remembers_it_and_only_goes_back_to_this_site(client):
    r = client.get("/lang/es?next=/help")
    assert r.status_code == 302 and r.headers["Location"].endswith("/help") and "lang=es" in r.headers["Set-Cookie"]
    assert client.get("/lang/so?next=//evil.example").headers["Location"].endswith("/")
    assert "lang=en" in client.get("/lang/xx").headers["Set-Cookie"]


def test_switching_language_keeps_the_answers(client):
    client.set_cookie("lang", "es")
    html = client.post("/", data=demo(action="relang", alive_0="Yes", alive_1="Yes", q_tod="No", you="Ana")
                       ).get_data(as_text=True)
    assert "<iframe" in html and "Ana, este es su plan" in html and "Todavía no está protegida" in html


def test_english_stays_the_default(client):
    html = client.get("/").get_data(as_text=True)
    assert 'lang="en"' in html and "Check this home" in html and "translated with the help of AI" not in html


def test_translated_about_page_shows_the_teams_own_ai_section(client):
    from web.content import load
    english = load("about").section("Use of AI tools")
    spanish = load("about", "es").section("Uso de herramientas de IA")
    assert spanish is not None and spanish.html == english.html
