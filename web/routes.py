"""The web pages: Check my home, Who would inherit?, What is a tangled title?, About.

Nothing typed is saved. Each click sends the whole form, and the page is rebuilt from it.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from itertools import groupby

import folium
from flask import Blueprint, Response, redirect, render_template, request
from markupsafe import escape

from titlecheck.assess import UNSURE, assess, pretty, record_notes, why_it_matters
from titlecheck.checklist import build_homestead_pdf, build_pdf
from titlecheck.demo import DEMO, DEMO_NEIGHBORS
from titlecheck.geo import FT_PER_M, analyze
from titlecheck.heirs import Child, Family, frozen_equity, generations, share_values, who_inherits
from titlecheck.homestead import explainer, homestead_plan
from titlecheck.i18n import LANGS, get_lang, set_lang, t
from titlecheck.lookup import AUDITOR_PARCEL_LINK, AddressLookupError, Parcel, find_nearby, find_parcels
from titlecheck.parcel_map import build_map
from titlecheck.places import BY_KEY, PLACES
from titlecheck.resources import FACTS, GLOSSARY, LINKS, link
from web.checkup import homestead_questions, role_question, title_questions
from web.content import load as load_content
from web.personal import clean_name, greeting, owners_phrase, summary

bp = Blueprint("pages", __name__)
PLACE_NAMES = {p.key: p.name for p in PLACES}

# colors for the inheritance chart, one per heir, and the generations chart
SLICE_COLORS = ["#1a73e8", "#e37400", "#1e8e3e", "#9334e6", "#c5221f", "#12b5cb", "#f9ab00", "#5f6368",
                "#e52592", "#7cb342"]
MAX_CHILDREN = 10
EXAMPLE_HOME_VALUE = 200_000     # shown until the family types their own home's value
MAX_HOME_VALUE = 10_000_000


# ------------------------------------------------------------------ check my home
def _record(p: Parcel) -> dict:
    """What the County record says, flattened into the hidden fields that ride along with every click."""
    return {"pid": p.parcel_id, "addr": p.address, "owners": p.owners,
            "years": "" if p.years_since_transfer is None else str(p.years_since_transfer),
            "year": f"{p.last_transfer:%Y}" if p.last_transfer else ""}


def _record_from_form(form) -> dict | None:
    if not form.get("pid"):
        return None
    return {"pid": form["pid"], "addr": form.get("addr", ""), "owners": form.getlist("owners"),
            "years": form.get("years", ""), "year": form.get("year", ""), "lot": form.get("lot", "")}


def _map_section(p: Parcel) -> dict:
    """Lot size, neighbors and the map's HTML for a home with a lot outline. Asks the County for the block once."""
    demo = p.parcel_id == "DEMO"
    nearby, warning = DEMO_NEIGHBORS if demo else None, None
    if not demo:
        try:
            nearby = find_nearby(p)
        except AddressLookupError:
            warning = t("The County's map service didn't answer, so only your lot is shown. Try again in a minute.")
    shape, neighbors = analyze(p.rings, {n.parcel_id: n.rings for n in nearby or []})
    by_id = {n.parcel_id: n for n in nearby or []}
    lot = t("{acres} acres ({sq_ft} sq ft)", acres=f"{shape.acres:.2f}", sq_ft=f"{shape.area_sq_ft:,.0f}")
    if shape.frontage_ft:
        lot += t(", about {feet} ft along the street", feet=f"{shape.frontage_ft:,.0f}")
    return {"demo": demo, "warning": warning, "lot": lot,
            "map_html": build_map(p, nearby or [], neighbors, shape, demo=demo).get_root().render(),
            "neighbors": [{"where": t(n.position), "address": by_id[n.key].address,
                           "owners": ", ".join(pretty(o) for o in by_id[n.key].owners) or t("No owner listed"),
                           "shared": f"{n.shared_m * FT_PER_M:,.0f} ft" if n.shared_m else "-"} for n in neighbors]}


def _plan(record: dict, form) -> dict:
    """Steps 2 and 3, plus the optional homestead check, from the record and the answers so far."""
    owners = record["owners"]
    role_q, role = role_question(form)
    name = clean_name(form.get("you"))
    questions, answers = title_questions(owners, form)
    result = assess(owners, answers)
    hs_questions, hs_answers = homestead_questions(form, owners_phrase(owners, "or", role))
    homestead = homestead_plan(hs_answers, result.status, record["pid"], owners_phrase(owners, "and", role))
    years = int(record["years"]) if record["years"].isdigit() else None
    return {"questions": questions, "result": result, "notes": record_notes(owners, years),
            "role_q": role_q, "role": role, "you": name, "greeting": greeting(name),
            "summary": summary(result.status, role, owners, answers.owners_alive),
            "hs_questions": hs_questions, "homestead": homestead, "places": BY_KEY,
            "roadmap_key": f"{record['pid']}|{record['addr']}|{result.status}",
            "hs_open": any(k.startswith("q_hs_") for k in form)}


def _manual_parcel(names: str, address: str) -> Parcel | None:
    owners = [n.strip().upper() for n in names.splitlines() if n.strip()]
    # typed names are 'First Last'; store them the County's way ('LAST FIRST') so display matches
    owners = [" ".join(n.split()[-1:] + n.split()[:-1]) for n in owners]
    return Parcel("MANUAL", address or t("Entered by hand"), "", owners, None, "") if owners else None


@bp.route("/", methods=["GET", "POST"])
def check():
    form = request.form
    page = {"address": form.get("address", ""), "error": None, "notice": None, "matches": None, "manual": False}
    record = _record_from_form(form)
    parcel = None
    action = form.get("action")

    if action == "demo":
        parcel = DEMO
    elif action == "relang" and record is not None:
        # the visitor switched language: look the same home up again (for the map), keeping every answer
        if record["pid"] == "DEMO":
            parcel = DEMO
        elif record["pid"] != "MANUAL":
            try:
                parcel = next((m for m in find_parcels(record["addr"]) if m.parcel_id == record["pid"]), None)
            except AddressLookupError:
                parcel = None
    elif action == "manual":
        parcel = _manual_parcel(form.get("names", ""), page["address"])
        page["manual"] = parcel is None
    elif action in ("lookup", "pick"):
        try:
            matches = find_parcels(page["address"])
        except AddressLookupError as e:
            page["error"], page["manual"], matches = t(str(e)), True, None
        if matches is not None:
            chosen = [m for m in matches if m.parcel_id == form.get("pick")] if action == "pick" else matches
            if not matches:
                page["notice"] = t("No Franklin County property matched that address. Check the spelling, or type the "
                                   "owner names yourself below. You can also search the {search}.",
                                   search=link("auditor_search"))
                page["manual"] = True
            elif len(chosen) == 1:
                parcel = chosen[0]
            else:
                page["matches"] = [{"pid": m.parcel_id, "label": f"{m.address}, {m.zip_code}"} for m in matches]

    if parcel is not None:
        record = _record(parcel)
        if parcel.rings:
            page.update(_map_section(parcel))
            record["lot"] = page["lot"]
        else:
            record["lot"] = ""
            page["no_map"] = True

    if record is not None:
        pid = record["pid"]
        page.update(record=record, owners_shown=[pretty(o) for o in record["owners"]],
                    auditor_link=AUDITOR_PARCEL_LINK.format(parcel=pid) if pid not in ("DEMO", "MANUAL") else None,
                    explainer=explainer(), why=why_it_matters(), **_plan(record, form))
        if request.headers.get("X-Partial"):
            return render_template("_answers.html", **page)
    return render_template("check.html", **page)


def _pdf_inputs():
    record = _record_from_form(request.form)
    if record is None:
        return None, None
    return record, _plan(record, request.form)


def _pdf_response(data: bytes, name: str) -> Response:
    return Response(data, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename={name}"})


@bp.post("/plan.pdf")
def plan_pdf():
    record, plan = _pdf_inputs()
    if record is None:
        return Response(t("Look up a home first."), status=400)
    details = [t("County parcel ID: {pid}", pid=record["pid"])] if record["pid"] not in ("DEMO", "MANUAL") else []
    if record["lot"]:
        details.append(t("Lot size: {lot}", lot=record["lot"]))
    return _pdf_response(build_pdf(plan["result"], record["addr"], plan["notes"], details,
                                   prepared_for=plan["you"], summary=plan["summary"], places=PLACE_NAMES),
                         "homekeep-action-plan.pdf")


@bp.post("/homestead.pdf")
def homestead_pdf():
    record, plan = _pdf_inputs()
    if record is None:
        return Response(t("Look up a home first."), status=400)
    return _pdf_response(build_homestead_pdf(plan["homestead"], record["addr"], prepared_for=plan["you"]),
                         "homestead-checklist.pdf")


# ------------------------------------------------------------------ free help near you
def _help_map() -> str:
    lat = sum(p.point[0] for p in PLACES) / len(PLACES)
    lon = sum(p.point[1] for p in PLACES) / len(PLACES)
    m = folium.Map(location=[lat, lon], zoom_start=14, tiles="OpenStreetMap", control_scale=True)
    for building, places in groupby(sorted(PLACES, key=lambda p: p.point), key=lambda p: p.point):
        places = list(places)
        html = "".join(f"<p style='margin:0 0 6px'><b>{escape(p.name)}</b><br>{escape(p.address)}<br>"
                       f"{escape(p.phone)}</p>" for p in places)
        folium.Marker(list(building), tooltip=" · ".join(p.name for p in places),
                      popup=folium.Popup(html, max_width=280),
                      icon=folium.Icon(color="darkblue" if len(places) > 1 else "green", icon="info-sign")).add_to(m)
    m.fit_bounds([[min(p.point[0] for p in PLACES), min(p.point[1] for p in PLACES)],
                  [max(p.point[0] for p in PLACES), max(p.point[1] for p in PLACES)]], padding=(60, 60))
    return m.get_root().render()


@bp.get("/help")
def help_near_you():
    return render_template("help.html", places=PLACES, map_html=_help_map(), links=LINKS)


# ------------------------------------------------------------------ who would inherit?
def _int(value, low: int, high: int, default: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def _dollars(text: str | None) -> int:
    """'$185,000' -> 185000. Starts with an example value; a cleared box means no dollar amounts."""
    if text is None:
        return EXAMPLE_HOME_VALUE
    digits = re.sub(r"\D", "", text.split(".")[0])
    return min(int(digits), MAX_HOME_VALUE) if digits else 0


@bp.route("/inherit", methods=["GET", "POST"])
def inherit():
    form = request.form
    # an unticked box is simply missing from a form, so a box only counts as unticked if it was on the page last time
    spouse = form.get("spouse") == "on"
    had_spouse_boxes = form.get("spouse_was") == "on"
    count = _int(form.get("count"), 0, MAX_CHILDREN, 2)
    children = []
    for i in range(count):
        shown = f"name_{i}" in form
        name = (form.get(f"name_{i}") or "").strip()[:40] or t("Child {n}", n=i + 1)
        living = form.get(f"living_{i}") == "on" if shown else True
        grandkids = _int(form.get(f"gk_{i}"), 0, 10, 0) if not living else 0
        with_spouse = form.get(f"ws_{i}") == "on" if shown and had_spouse_boxes else True
        children.append(Child(name, living, grandkids, with_spouse))
    ask_parents = not any(c.living or c.grandchildren for c in children) and not spouse
    parents = _int(form.get("parents"), 0, 2, 0) if ask_parents else 0
    siblings = _int(form.get("siblings"), 0, 15, 0) if ask_parents else 0
    result = who_inherits(Family(spouse, children, parents, siblings))
    value = _dollars(form.get("value"))

    slices, start = [], 0.0
    for i, (h, worth) in enumerate(zip(result.heirs, share_values(result, value))):
        pct = float(h.share) * 100
        slices.append({"name": h.name, "fraction": str(h.share), "percent": f"{pct:.1f}%", "worth": worth,
                       "color": SLICE_COLORS[i % len(SLICE_COLORS)], "start": start, "end": start + pct})
        start += pct
    kids, gens = _int(form.get("kids"), 1, 5, 3), _int(form.get("gens"), 1, 5, 3)
    rows = generations(kids, gens)
    top = rows[-1][1]
    bars = [{"label": t("Original owner") if g == 0 else t("Generation {n}", n=g), "owners": o, "height": max(2, 100 * o / top)}
            for g, o in rows]
    page = {"spouse": spouse, "count": count, "children": children, "ask_parents": ask_parents, "parents": parents,
            "siblings": siblings, "result": result, "slices": slices, "kids": kids, "gens": gens, "bars": bars,
            "last": top, "max_children": MAX_CHILDREN, "tod_link": link("tod_forms"),
            "value": value, "frozen": frozen_equity(result, value), "piece": round(value / top) if value else 0,
            "is_example": form.get("value") is None}
    if request.headers.get("X-Partial"):
        return render_template("_inherit.html", **page)
    return render_template("inherit.html", **page)


# ------------------------------------------------------------------ the two reading pages
@bp.get("/learn")
def learn():
    return render_template("learn.html", page=load_content("learn", get_lang()))


@bp.get("/about")
def about():
    return render_template("about.html", page=load_content("about", get_lang()), links=LINKS.values())


# ------------------------------------------------------------------ language
@bp.before_app_request
def pick_language():
    """?lang=es on any link switches for that page; otherwise use the language the visitor picked last time."""
    set_lang(request.args.get("lang") or request.cookies.get("lang"))


@bp.get("/lang/<code>")
def choose_language(code: str):
    target = request.args.get("next", "/")
    if not target.startswith("/") or target.startswith("//"):
        target = "/"                     # only ever send people back to a page on this site
    resp = redirect(target)
    resp.set_cookie("lang", code if code in LANGS else "en", max_age=365 * 24 * 3600, samesite="Lax",
                    httponly=True, secure=request.is_secure)
    return resp


@bp.app_context_processor
def common():
    return {"this_year": datetime.now(timezone.utc).year, "unsure": UNSURE, "glossary": GLOSSARY, "facts": FACTS,
            "langs": LANGS, "lang": get_lang()}
