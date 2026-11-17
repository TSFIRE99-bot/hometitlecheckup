"""HomeKeep Pro pages: the professional landing page, sign-in, the staff workspace, and the family upload page.

The free homeowner site (web/routes.py) never reads or writes anything here. Pages under /pro/app need a signed-in
staff member, and every query is scoped to that person's firm. Family pages under /f/<token> show only the items that
one person was asked for.
"""
from __future__ import annotations

import json
import time
from datetime import date
from functools import wraps

from flask import (Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request, session,
                   url_for)

from pro import billing, checklist, demo, extract, packet, store
from pro.documents import UploadRejected, check_upload
from pro.security import ROLE_NAMES, ROLES, Throttle, can, csrf_ok, csrf_token, password_problem

bp = Blueprint("pro", __name__, template_folder="templates")
login_throttle = Throttle()


def pro():
    return current_app.extensions["homekeep_pro"]


def db():
    return pro()["engine"].begin()


# ------------------------------------------------------------------ request setup and protection
@bp.before_request
def prepare():
    state = pro()
    if state["cfg"].demo_enabled and not state.get("seeded"):
        with db() as conn:
            state["demo_firm"] = demo.seed(conn, state["cfg"])
        state["seeded"] = True
    if time.monotonic() - state.get("purged", 0) > 3600:
        with db() as conn:
            store.purge_expired(conn)
        state["purged"] = time.monotonic()
    if request.method == "POST" and not csrf_ok(session, request.form.get("csrf")):
        abort(400, "This form expired. Go back, reload the page and try again.")
    g.user = g.firm = None
    if "uid" in session:
        with db() as conn:
            g.user = store.get_user(conn, session.get("fid"), session["uid"])
            g.firm = store.get_firm(conn, session.get("fid")) if g.user else None
        if g.user is None:
            session.clear()


@bp.after_request
def protect(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"       # family links carry a token in the address
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.app_context_processor
def pro_context():
    cfg = current_app.extensions["homekeep_pro"]["cfg"]
    return {"csrf": lambda: csrf_token(session), "pro_user": getattr(g, "user", None),
            "pro_firm": getattr(g, "firm", None), "can": lambda p: bool(getattr(g, "user", None)) and can(g.user.role, p),
            "role_names": ROLE_NAMES, "staging_notes": staging_notes(cfg)}


def staging_notes(cfg) -> list[str]:
    notes = []
    if cfg.database_url.startswith("sqlite:////tmp"):
        notes.append("Staging: data is kept in temporary storage and resets when the server restarts. "
                     "Do not upload real documents.")
    if cfg.secret_is_ephemeral:
        notes.append("Staging: sign-ins can reset because no permanent session key is configured.")
    return notes


def signed_in(permission: str | None = None):
    def wrap(view):
        @wraps(view)
        def inner(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("pro.login", next=request.path))
            if permission and not can(g.user.role, permission):
                abort(403)
            return view(*args, **kwargs)
        return inner
    return wrap


def actor() -> str:
    return f"user:{g.user.id}"


def load_case(conn, case_id: int):
    case = store.get_case(conn, g.firm.id, case_id)
    if case is None:
        abort(404)                    # another firm's case looks exactly like a case that doesn't exist
    return case


def family_link(token: str) -> str:
    return url_for("pro.family", token=token, _external=True)


# ------------------------------------------------------------------ public professional pages
@bp.get("/pro")
def landing():
    return render_template("pro/landing.html", plans=billing.plans(), demo=pro()["cfg"].demo_enabled)


@bp.post("/pro/request-demo")
def request_demo():
    form = request.form
    name, firm, email = (form.get(k, "").strip() for k in ("name", "firm", "email"))
    if not (name and firm and "@" in email and form.get("consent") == "yes"):
        flash("Please fill in your name, firm and email, and agree to be contacted.", "error")
        return redirect(url_for("pro.landing") + "#request")
    with db() as conn:
        store.save_demo_request(conn, name, firm, email, form.get("role", ""), form.get("message", ""), True)
    flash("Thank you. A HomeKeep founder will email you to set up a time. We don't add you to any mailing list.", "ok")
    return redirect(url_for("pro.landing") + "#request")


@bp.get("/pro/security")
def security():
    return render_template("pro/security.html", cfg=pro()["cfg"])


@bp.route("/pro/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not login_throttle.allow(email or request.remote_addr or "?"):
            flash("Too many tries. Wait ten minutes and try again.", "error")
            return render_template("pro/login.html"), 429
        with db() as conn:
            user = store.authenticate(conn, email, request.form.get("password", ""))
            if user is not None:
                store.log(conn, user.firm_id, None, f"user:{user.id}", "signed_in")
        if user is None:
            flash("That email and password don't match.", "error")
            return render_template("pro/login.html"), 401
        session.clear()
        session.update(uid=user.id, fid=user.firm_id)
        target = request.args.get("next", "")
        return redirect(target if target.startswith("/pro/app") else url_for("pro.cases"))
    return render_template("pro/login.html", demo=pro()["cfg"].demo_enabled)


@bp.post("/pro/demo")
def start_demo():
    cfg = pro()["cfg"]
    if not cfg.demo_enabled:
        abort(404)
    role = request.form.get("role", "staff")
    with db() as conn:
        user = demo.demo_user(conn, demo.seed(conn, cfg), role if role in ROLES else "staff")
    session.clear()
    session.update(uid=user.id, fid=user.firm_id)
    flash("You're in the fictional demo firm. Everyone and everything here is made up.", "ok")
    return redirect(url_for("pro.cases"))


@bp.post("/pro/logout")
def logout():
    session.clear()
    return redirect(url_for("pro.landing"))


@bp.route("/pro/signup", methods=["GET", "POST"])
def signup():
    if not pro()["cfg"].signup_enabled:
        return render_template("pro/notice.html", title="Sign-up is by invitation",
                               text="HomeKeep Pro is in a small pilot. Request a demo and we'll set up your firm."), 404
    if request.method == "POST":
        form = request.form
        problem = password_problem(form.get("password", ""))
        with db() as conn:
            if not form.get("firm") or not form.get("name") or "@" not in form.get("email", ""):
                problem = "Fill in every field."
            elif store.email_taken(conn, form["email"]):
                problem = "That email already has an account."
            if problem:
                flash(problem, "error")
                return render_template("pro/signup.html"), 400
            firm_id, user_id = store.create_firm(conn, form["firm"], form["email"], form["name"], form["password"])
        session.clear()
        session.update(uid=user_id, fid=firm_id)
        return redirect(url_for("pro.cases"))
    return render_template("pro/signup.html")


@bp.route("/pro/join/<token>", methods=["GET", "POST"])
def join(token: str):
    with db() as conn:
        invite = store.open_invite(conn, token)
        if invite is None:
            return render_template("pro/notice.html", title="This invitation has expired or was already used",
                                   text="Ask the person who invited you to send a new one."), 404
        if request.method == "POST":
            problem = password_problem(request.form.get("password", "")) or (
                None if request.form.get("name", "").strip() else "Enter your name.")
            if problem:
                flash(problem, "error")
                return render_template("pro/join.html", invite=invite), 400
            user = store.accept_invite(conn, token, request.form["name"].strip(), request.form["password"])
            if user is None:
                flash("This email already has an account.", "error")
                return render_template("pro/join.html", invite=invite), 400
            session.clear()
            session.update(uid=user.id, fid=user.firm_id)
            return redirect(url_for("pro.cases"))
        return render_template("pro/join.html", invite=invite)


# ------------------------------------------------------------------ staff workspace: cases
@bp.get("/pro/app")
@signed_in("cases")
def cases():
    with db() as conn:
        rows = store.list_cases(conn, g.firm.id, include_closed=request.args.get("closed") == "1")
        summary = {c.id: (len(checklist.outstanding(store.case_items(conn, g.firm.id, c.id))),
                          sum(1 for f in store.fact_summary(conn, g.firm.id, c.id)
                              if f["state"] in ("conflicting", "awaiting_review"))) for c in rows}
        people = {u.id: u.name for u in store.staff(conn, g.firm.id)}
        plan = billing.plan_for(g.firm.plan)
        used = store.matters_this_period(conn, g.firm)
    return render_template("pro/cases.html", cases=rows, summary=summary, people=people, plan=plan, used=used,
                           statuses=store.CASE_STATUSES)


@bp.post("/pro/app/cases")
@signed_in("cases")
def create_case():
    form = request.form
    try:
        with db() as conn:
            case_id = store.create_case(conn, g.firm.id, g.user.id, form.get("reference", ""), form.get("title", ""),
                                        form.get("decedent", ""), form.get("address", ""), form.get("parcel", ""))
    except store.LimitReached as e:
        flash(str(e), "error")
        return redirect(url_for("pro.cases"))
    return redirect(url_for("pro.case", case_id=case_id))


@bp.get("/pro/app/cases/<int:case_id>")
@signed_in("cases")
def case(case_id: int):
    with db() as conn:
        c = load_case(conn, case_id)
        data = {
            "case": c, "items": store.case_items(conn, g.firm.id, case_id),
            "participants": store.case_participants(conn, g.firm.id, case_id),
            "documents": store.list_documents(conn, g.firm.id, case_id),
            "facts": store.fact_summary(conn, g.firm.id, case_id),
            "activity": store.case_activity(conn, g.firm.id, case_id),
            "outbox": store.case_outbox(conn, g.firm.id, case_id),
            "templates": store.firm_templates(conn, g.firm.id),
            "staff": store.staff(conn, g.firm.id),
            "usage": store.usage_totals(conn, g.firm.id, case_id),
            "record": json.loads(c.record_source) if c.record_source else None,
        }
    requests_by_person = {}
    with db() as conn:
        for p in data["participants"]:
            requests_by_person[p.id] = [i.label for i in store.participant_requests(conn, p)]
    return render_template("pro/case.html", **data, requests_by_person=requests_by_person,
                           statuses=store.CASE_STATUSES, item_labels=checklist.STATUS_LABELS,
                           doc_types=extract.DOC_TYPES, outstanding=checklist.outstanding(data["items"]),
                           family_items=[i for i in data["items"] if checklist.BY_KEY.get(i.key) is None
                                         or checklist.BY_KEY[i.key].family_can_provide])


@bp.post("/pro/app/cases/<int:case_id>/update")
@signed_in("cases")
def update_case(case_id: int):
    form = request.form
    changes = {}
    if form.get("status") in store.CASE_STATUSES:
        changes["status"] = form["status"]
    if form.get("assigned_to", "").isdigit():
        changes["assigned_to"] = int(form["assigned_to"])
    with db() as conn:
        load_case(conn, case_id)
        if "assigned_to" in changes and store.get_user(conn, g.firm.id, changes["assigned_to"]) is None:
            abort(400)
        store.update_case(conn, g.firm.id, case_id, g.user.id, **changes)
    return redirect(url_for("pro.case", case_id=case_id))


@bp.post("/pro/app/cases/<int:case_id>/items/<int:item_id>")
@signed_in("cases")
def set_item(case_id: int, item_id: int):
    status = request.form.get("status", "")
    if status == "approved" and not can(g.user.role, "approve"):
        abort(403)
    with db() as conn:
        load_case(conn, case_id)
        store.set_item_status(conn, g.firm.id, case_id, item_id, status, actor(), request.form.get("note", ""))
    return redirect(url_for("pro.case", case_id=case_id) + "#checklist")


@bp.post("/pro/app/cases/<int:case_id>/record")
@signed_in("cases")
def attach_record(case_id: int):
    """Looks the property up in the Franklin County Auditor's public records and saves where and when."""
    from titlecheck.lookup import AUDITOR_PARCEL_LINK, AddressLookupError, find_parcels
    with db() as conn:
        c = load_case(conn, case_id)
    if not c.property_address or (c.parcel_id or "").upper().startswith("DEMO"):
        flash("Fictional demo properties have no County record. Enter a real Franklin County address to try this.",
              "error")
        return redirect(url_for("pro.case", case_id=case_id))
    try:
        matches = find_parcels(c.property_address)
    except AddressLookupError as e:
        flash(f"The County lookup didn't work: {e}", "error")
        return redirect(url_for("pro.case", case_id=case_id))
    match = next((m for m in matches if not c.parcel_id or m.parcel_id == c.parcel_id), None)
    if match is None:
        flash("No matching County record. Check the address and parcel number.", "error")
        return redirect(url_for("pro.case", case_id=case_id))
    record = {"url": AUDITOR_PARCEL_LINK.format(parcel=match.parcel_id), "retrieved": f"{date.today():%Y-%m-%d}",
              "parcel": match.parcel_id, "owners_as_listed": match.owners,
              "last_transfer": f"{match.last_transfer:%Y-%m-%d}" if match.last_transfer else None,
              "limits": ("The Auditor's owner field is a tax record. It is not proof of legal title, and it does not "
                         "show whether anyone named has died.")}
    with db() as conn:
        store.set_record_source(conn, g.firm.id, case_id, g.user.id, record)
        for owner in match.owners:
            store.add_field(conn, g.firm.id, case_id, "tax_owner", owner, "record", actor(),
                            evidence=f"Franklin County Auditor record {match.parcel_id}, retrieved {record['retrieved']}")
    flash("County record attached. Its owner field is a tax record, not proof of title.", "ok")
    return redirect(url_for("pro.case", case_id=case_id))


@bp.post("/pro/app/cases/<int:case_id>/delete")
@signed_in("delete")
def delete_case(case_id: int):
    with db() as conn:
        c = load_case(conn, case_id)
        if request.form.get("confirm", "").strip() != c.reference:
            flash(f"To delete, type the matter number {c.reference} exactly.", "error")
            return redirect(url_for("pro.case", case_id=case_id) + "#danger")
        store.delete_case(conn, g.firm.id, case_id, actor())
    flash(f"Case {c.reference} and its documents were deleted.", "ok")
    return redirect(url_for("pro.cases"))


# ------------------------------------------------------------------ family participants and follow-ups
@bp.post("/pro/app/cases/<int:case_id>/participants")
@signed_in("cases")
def add_participant(case_id: int):
    form = request.form
    item_ids = [int(i) for i in form.getlist("items") if i.isdigit()]
    if not form.get("name", "").strip() or not item_ids:
        flash("Enter the person's name and choose at least one thing to ask them for.", "error")
        return redirect(url_for("pro.case", case_id=case_id) + "#family")
    with db() as conn:
        load_case(conn, case_id)
        token = store.add_participant(conn, pro()["cfg"], g.firm.id, case_id, g.user.id, form["name"],
                                      form.get("email", ""), form.get("relation", ""), item_ids,
                                      form.get("consent") == "yes")
    flash(f"Family link (shown once; copy it now): {family_link(token)}", "link")
    return redirect(url_for("pro.case", case_id=case_id) + "#family")


@bp.post("/pro/app/cases/<int:case_id>/participants/<int:pid>/<action>")
@signed_in("cases")
def participant_action(case_id: int, pid: int, action: str):
    cfg = pro()["cfg"]
    with db() as conn:
        load_case(conn, case_id)
        if action == "renew":
            token = store.renew_participant_link(conn, cfg, g.firm.id, case_id, pid, g.user.id)
            flash(f"New family link (the old one stops working; copy this now): {family_link(token)}", "link")
        elif action == "revoke":
            store.revoke_participant(conn, g.firm.id, case_id, pid, g.user.id)
            flash("The family link no longer works.", "ok")
        elif action == "consent":
            store.record_consent(conn, g.firm.id, case_id, pid, g.user.id, request.form.get("agreed") == "yes")
        elif action == "message":
            if not can(g.user.role, "send"):
                abort(403)
            token = store.renew_participant_link(conn, cfg, g.firm.id, case_id, pid, g.user.id)
            ok, text = store.send_follow_up(conn, cfg, g.firm.id, case_id, pid,
                                            int(request.form.get("template", "0") or 0), g.user.id, family_link(token))
            if not ok:
                raise _Rollback(text, case_id)
            flash(text, "ok")
        else:
            abort(404)
    return redirect(url_for("pro.case", case_id=case_id) + "#family")


class _Rollback(Exception):
    """Undo a renewed link when the follow-up it was made for is refused."""

    def __init__(self, text: str, case_id: int):
        super().__init__(text)
        self.text, self.case_id = text, case_id


@bp.errorhandler(_Rollback)
def rolled_back(e: _Rollback):
    flash(e.text, "error")
    return redirect(url_for("pro.case", case_id=e.case_id) + "#family")


# ------------------------------------------------------------------ documents
@bp.post("/pro/app/cases/<int:case_id>/documents")
@signed_in("cases")
def staff_upload(case_id: int):
    cfg = pro()["cfg"]
    upload = request.files.get("file")
    item_id = request.form.get("item", "")
    try:
        checked = check_upload(upload.filename if upload else "", upload.read(cfg.max_upload_bytes + 1) if upload
                               else b"", cfg.max_upload_bytes)
        with db() as conn:
            load_case(conn, case_id)
            valid_items = {i.id for i in store.case_items(conn, g.firm.id, case_id)}
            doc_id = store.store_document(conn, cfg, g.firm.id, case_id, checked,
                                          item_id=int(item_id) if item_id.isdigit() and int(item_id) in valid_items
                                          else None, uploaded_by=g.user.id)
            store.release_document(conn, g.firm.id, case_id, doc_id, g.user.id)   # staff uploads are trusted
        flash(f"Uploaded {checked.filename}.", "ok")
    except UploadRejected as e:
        flash(str(e), "error")
    return redirect(url_for("pro.case", case_id=case_id) + "#documents")


@bp.post("/pro/app/cases/<int:case_id>/documents/<int:doc_id>/<action>")
@signed_in("cases")
def document_action(case_id: int, doc_id: int, action: str):
    with db() as conn:
        load_case(conn, case_id)
        if action == "release":
            store.release_document(conn, g.firm.id, case_id, doc_id, g.user.id)
        elif action == "delete":
            if not can(g.user.role, "delete"):
                abort(403)
            store.delete_document(conn, g.firm.id, case_id, doc_id, g.user.id, request.form.get("reason", ""))
            flash("Document deleted. Unreviewed values taken from it were removed too.", "ok")
        else:
            abort(404)
    return redirect(url_for("pro.case", case_id=case_id) + "#documents")


@bp.get("/pro/app/cases/<int:case_id>/documents/<int:doc_id>/download")
@signed_in("cases")
def download(case_id: int, doc_id: int):
    with db() as conn:
        load_case(conn, case_id)
        doc = store.get_document(conn, g.firm.id, case_id, doc_id)
        if doc is None:
            abort(404)
        if doc.status == "quarantined":
            flash("Release this file before opening it. It came from outside the firm and hasn't been checked.",
                  "error")
            return redirect(url_for("pro.case", case_id=case_id) + "#documents")
        store.log(conn, g.firm.id, case_id, actor(), "document_downloaded", doc.filename)
    return Response(doc.data, mimetype="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'})


# ------------------------------------------------------------------ review
@bp.get("/pro/app/cases/<int:case_id>/review")
@signed_in("review")
def review(case_id: int):
    with db() as conn:
        c = load_case(conn, case_id)
        facts = store.fact_summary(conn, g.firm.id, case_id)
        docs = {d.id: d for d in store.list_documents(conn, g.firm.id, case_id, include_deleted=True)}
        history = {f.id: store.field_history_for(conn, g.firm.id, f.id) for fact in facts for f in fact["fields"]}
        people = {p.id: p.name for p in store.case_participants(conn, g.firm.id, case_id)}
        staff_names = {u.id: u.name for u in store.staff(conn, g.firm.id)}
        warnings = [a for a in store.case_activity(conn, g.firm.id, case_id) if a.action == "document_warning"]
    return render_template("pro/review.html", case=c, facts=facts, docs=docs, history=history, people=people,
                           staff_names=staff_names, warnings=warnings, labels=extract.FIELD_LABELS)


@bp.post("/pro/app/cases/<int:case_id>/fields/<int:field_id>")
@signed_in("review")
def review_field(case_id: int, field_id: int):
    form = request.form
    with db() as conn:
        load_case(conn, case_id)
        store.review_field(conn, g.firm.id, case_id, field_id, g.user.id, form.get("action", ""),
                           form.get("value", ""), form.get("reason", ""))
    return redirect(url_for("pro.review", case_id=case_id) + f"#field-{field_id}")


@bp.post("/pro/app/cases/<int:case_id>/fields")
@signed_in("review")
def add_staff_field(case_id: int):
    form = request.form
    with db() as conn:
        load_case(conn, case_id)
        store.add_field(conn, g.firm.id, case_id, form.get("key", ""), form.get("value", ""), "staff", actor(),
                        evidence=form.get("evidence", ""))
    return redirect(url_for("pro.review", case_id=case_id))


# ------------------------------------------------------------------ packet
@bp.get("/pro/app/cases/<int:case_id>/packet.<fmt>")
@signed_in("cases")
def case_packet(case_id: int, fmt: str):
    if fmt not in ("pdf", "json"):
        abort(404)
    with db() as conn:
        c = load_case(conn, case_id)
        data = packet.gather(conn, g.firm.id, case_id)
        from pro.db import cases as cases_table, now
        conn.execute(cases_table.update().where(cases_table.c.id == case_id).values(packet_ready_at=now()))
        store.log(conn, g.firm.id, case_id, actor(), "packet_exported", fmt)
    body = packet.as_pdf(data) if fmt == "pdf" else packet.as_json(data)
    return Response(body, mimetype="application/pdf" if fmt == "pdf" else "application/json",
                    headers={"Content-Disposition": f'attachment; filename="packet-{c.reference}.{fmt}"'})


# ------------------------------------------------------------------ firm settings
@bp.get("/pro/app/settings")
@signed_in()
def settings():
    with db() as conn:
        data = {"staff": store.staff(conn, g.firm.id), "templates": store.firm_templates(conn, g.firm.id),
                "plan": billing.plan_for(g.firm.plan), "used": store.matters_this_period(conn, g.firm),
                "period_start": store.period_start(g.firm), "storage": store.firm_storage_bytes(conn, g.firm.id),
                "usage": store.usage_totals(conn, g.firm.id), "cfg": pro()["cfg"],
                "measures": store.pilot_measures(conn, g.firm.id)}
    return render_template("pro/settings.html", **data, roles=ROLES, checklist_items=checklist.DEFAULT)


@bp.post("/pro/app/settings/<action>")
@signed_in()
def settings_action(action: str):
    form = request.form
    with db() as conn:
        if action == "invite" and can(g.user.role, "staff"):
            role = form.get("role") if form.get("role") in ("attorney", "staff") else "staff"
            email = form.get("email", "").strip()
            if "@" not in email or store.email_taken(conn, email):
                flash("Enter an email that doesn't already have an account.", "error")
            else:
                token = store.create_invite(conn, g.firm.id, email, role, g.user.id)
                flash(f"Invitation link for {email} (valid 7 days; copy it now): "
                      f"{url_for('pro.join', token=token, _external=True)}", "link")
        elif action in ("deactivate", "activate") and can(g.user.role, "staff"):
            store.set_staff_active(conn, g.firm.id, int(form.get("user", "0") or 0), action == "activate", g.user.id)
        elif action == "retention" and can(g.user.role, "settings"):
            store.set_retention(conn, g.firm.id, int(form.get("days", "365") or 365), g.user.id)
        elif action == "approve-checklist" and can(g.user.role, "approve"):
            store.approve_checklist(conn, g.firm.id, g.user.id)
        elif action == "template" and can(g.user.role, "send"):
            problem = store.save_template(conn, g.firm.id, int(form.get("template", "0") or 0), g.user.id,
                                          form.get("subject", ""), form.get("body", ""))
            flash(problem or "Template saved. It needs approval before use.", "error" if problem else "ok")
        elif action == "approve-template" and can(g.user.role, "approve"):
            store.approve_template(conn, g.firm.id, int(form.get("template", "0") or 0), g.user.id)
        else:
            abort(403)
    return redirect(url_for("pro.settings"))


# ------------------------------------------------------------------ family page (no account, expiring link)
def _participant(token: str):
    with db() as conn:
        person = store.participant_by_token(conn, token)
    if person is None:
        return None
    return person


@bp.get("/f/<token>")
def family(token: str):
    with db() as conn:
        person = store.participant_by_token(conn, token)
        if person is None:
            return render_template("pro/notice.html", title="This link has expired",
                                   text="Ask the law office that sent it for a new link."), 404
        asked = store.participant_requests(conn, person)
        uploads = store.participant_uploads(conn, person)
        firm = store.get_firm(conn, person.firm_id)
    return render_template("pro/family.html", person=person, asked=asked, uploads=uploads, firm=firm, token=token,
                           max_mb=pro()["cfg"].max_upload_bytes // (1024 * 1024))


@bp.post("/f/<token>/upload")
def family_upload(token: str):
    cfg = pro()["cfg"]
    with db() as conn:
        person = store.participant_by_token(conn, token)
        if person is None:
            abort(404)
        allowed = {i.id: i for i in store.participant_requests(conn, person)}
        item_id = int(request.form.get("item", "0") or 0)
        if item_id not in allowed or allowed[item_id].kind != "document":
            abort(403)                                     # only the items this person was asked for
    upload = request.files.get("file")
    try:
        checked = check_upload(upload.filename if upload else "", upload.read(cfg.max_upload_bytes + 1) if upload
                               else b"", cfg.max_upload_bytes)
        with db() as conn:
            store.store_document(conn, cfg, person.firm_id, person.case_id, checked, item_id=item_id,
                                 participant_id=person.id)
        flash(f"Thank you. {checked.filename} was sent to the law office.", "ok")
    except UploadRejected as e:
        flash(str(e), "error")
    return redirect(url_for("pro.family", token=token))


@bp.post("/f/<token>/info")
def family_info(token: str):
    with db() as conn:
        person = store.participant_by_token(conn, token)
        if person is None:
            abort(404)
        allowed = {i.id: i for i in store.participant_requests(conn, person)}
        item_id = int(request.form.get("item", "0") or 0)
        text = request.form.get("text", "").strip()[:2000]
        if item_id not in allowed or allowed[item_id].kind != "information" or not text:
            abort(403)
        item = allowed[item_id]
        if item.key == "family_tree":
            for line in text.splitlines()[:30]:
                store.add_field(conn, person.firm_id, person.case_id, "heir", line, "family",
                                f"participant:{person.id}", person.id)
        store.set_item_status(conn, person.firm_id, person.case_id, item_id, "received", f"participant:{person.id}",
                              "Answer given by family" if item.key == "family_tree" else text)
    flash("Thank you. Your answer was sent to the law office.", "ok")
    return redirect(url_for("pro.family", token=token))
