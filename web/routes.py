"""The web pages: Check my home, Who would inherit?, What is a tangled title?, About.

Nothing typed is saved. Each click sends the whole form, and the page is rebuilt from it.
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, Response, render_template, request

from titlecheck.assess import UNSURE, assess, pretty, record_notes, why_it_matters
from titlecheck.checklist import build_homestead_pdf, build_pdf
from titlecheck.demo import DEMO, DEMO_NEIGHBORS
from titlecheck.geo import FT_PER_M, analyze
from titlecheck.heirs import Child, Family, generations, who_inherits
from titlecheck.homestead import EXPLAINER, homestead_plan
from titlecheck.lookup import AUDITOR_PARCEL_LINK, AddressLookupError, Parcel, find_nearby, find_parcels
from titlecheck.parcel_map import build_map
from titlecheck.resources import FACTS, LINKS, link
from web.checkup import homestead_questions, title_questions

bp = Blueprint("pages", __name__)

# colors for the inheritance chart, one per heir, and the generations chart
SLICE_COLORS = ["#1a73e8", "#e37400", "#1e8e3e", "#9334e6", "#c5221f", "#12b5cb", "#f9ab00", "#5f6368",
                "#e52592", "#7cb342"]
MAX_CHILDREN = 10


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
            warning = "The County's map service didn't answer, so only your lot is shown. Try again in a minute."
    shape, neighbors = analyze(p.rings, {n.parcel_id: n.rings for n in nearby or []})
    by_id = {n.parcel_id: n for n in nearby or []}
    lot = f"{shape.acres:.2f} acres ({shape.area_sq_ft:,.0f} sq ft)"
    if shape.frontage_ft:
        lot += f", about {shape.frontage_ft:,.0f} ft along the street"
    return {"demo": demo, "warning": warning, "lot": lot,
            "map_html": build_map(p, nearby or [], neighbors, shape, demo=demo).get_root().render(),
            "neighbors": [{"where": n.position, "address": by_id[n.key].address,
                           "owners": ", ".join(pretty(o) for o in by_id[n.key].owners) or "No owner listed",
                           "shared": f"{n.shared_m * FT_PER_M:,.0f} ft" if n.shared_m else "-"} for n in neighbors]}


def _plan(record: dict, form) -> dict:
    """Steps 2 and 3, plus the optional homestead check, from the record and the answers so far."""
    owners = record["owners"]
    questions, answers = title_questions(owners, form)
    result = assess(owners, answers)
    hs_questions, hs_answers = homestead_questions(form)
    years = int(record["years"]) if record["years"].isdigit() else None
    return {"questions": questions, "result": result, "notes": record_notes(owners, years),
            "hs_questions": hs_questions, "homestead": homestead_plan(hs_answers, result.status),
            "hs_open": any(k.startswith("q_hs_") for k in form)}


def _manual_parcel(names: str, address: str) -> Parcel | None:
    owners = [n.strip().upper() for n in names.splitlines() if n.strip()]
    # typed names are 'First Last'; store them the County's way ('LAST FIRST') so display matches
    owners = [" ".join(n.split()[-1:] + n.split()[:-1]) for n in owners]
    return Parcel("MANUAL", address or "Entered by hand", "", owners, None, "") if owners else None


@bp.route("/", methods=["GET", "POST"])
def check():
    form = request.form
    page = {"address": form.get("address", ""), "error": None, "notice": None, "matches": None, "manual": False}
    record = _record_from_form(form)
    parcel = None
    action = form.get("action")

    if action == "demo":
        parcel = DEMO
    elif action == "manual":
        parcel = _manual_parcel(form.get("names", ""), page["address"])
        page["manual"] = parcel is None
    elif action in ("lookup", "pick"):
        try:
            matches = find_parcels(page["address"])
        except AddressLookupError as e:
            page["error"], page["manual"], matches = str(e), True, None
        if matches is not None:
            chosen = [m for m in matches if m.parcel_id == form.get("pick")] if action == "pick" else matches
            if not matches:
                page["notice"] = ("No Franklin County property matched that address. Check the spelling, or type "
                                  f"the owner names yourself below. You can also search the {link('auditor_search')}.")
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
                    explainer=EXPLAINER, why=why_it_matters(), **_plan(record, form))
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
        return Response("Look up a home first.", status=400)
    details = [f"County parcel ID: {record['pid']}"] if record["pid"] not in ("DEMO", "MANUAL") else []
    if record["lot"]:
        details.append(f"Lot size: {record['lot']}")
    return _pdf_response(build_pdf(plan["result"], record["addr"], plan["notes"], details),
                         "home-title-action-plan.pdf")


@bp.post("/homestead.pdf")
def homestead_pdf():
    record, plan = _pdf_inputs()
    if record is None:
        return Response("Look up a home first.", status=400)
    return _pdf_response(build_homestead_pdf(plan["homestead"], record["addr"]), "homestead-checklist.pdf")


# ------------------------------------------------------------------ who would inherit?
def _int(value, low: int, high: int, default: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


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
        name = (form.get(f"name_{i}") or "").strip()[:40] or f"Child {i + 1}"
        living = form.get(f"living_{i}") == "on" if shown else True
        grandkids = _int(form.get(f"gk_{i}"), 0, 10, 0) if not living else 0
        with_spouse = form.get(f"ws_{i}") == "on" if shown and had_spouse_boxes else True
        children.append(Child(name, living, grandkids, with_spouse))
    ask_parents = not any(c.living or c.grandchildren for c in children) and not spouse
    parents = _int(form.get("parents"), 0, 2, 0) if ask_parents else 0
    siblings = _int(form.get("siblings"), 0, 15, 0) if ask_parents else 0
    result = who_inherits(Family(spouse, children, parents, siblings))

    slices, start = [], 0.0
    for i, h in enumerate(result.heirs):
        pct = float(h.share) * 100
        slices.append({"name": h.name, "fraction": str(h.share), "percent": f"{pct:.1f}%",
                       "color": SLICE_COLORS[i % len(SLICE_COLORS)], "start": start, "end": start + pct})
        start += pct
    kids, gens = _int(form.get("kids"), 1, 5, 3), _int(form.get("gens"), 1, 5, 3)
    rows = generations(kids, gens)
    top = rows[-1][1]
    bars = [{"label": "Original owner" if g == 0 else f"Generation {g}", "owners": o, "height": max(2, 100 * o / top)}
            for g, o in rows]
    page = {"spouse": spouse, "count": count, "children": children, "ask_parents": ask_parents, "parents": parents,
            "siblings": siblings, "result": result, "slices": slices, "kids": kids, "gens": gens, "bars": bars,
            "last": top, "max_children": MAX_CHILDREN, "tod_link": link("tod_forms")}
    if request.headers.get("X-Partial"):
        return render_template("_inherit.html", **page)
    return render_template("inherit.html", **page)


# ------------------------------------------------------------------ the two reading pages
@bp.get("/learn")
def learn():
    return render_template("learn.html", facts=FACTS, tod_link=link("tod_forms"))


@bp.get("/about")
def about():
    return render_template("about.html", links=LINKS.values())


@bp.app_context_processor
def common():
    return {"this_year": datetime.now(timezone.utc).year, "unsure": UNSURE}
