"""Every read and write of HomeKeep Pro data. Each function that touches case data takes firm_id and filters on it,
so a request signed in to one firm cannot reach another firm's rows even with a guessed ID.
"""
from __future__ import annotations

import json
import statistics
from datetime import timedelta

from sqlalchemy import and_, delete, func, insert, select, update

from pro import billing, checklist, extract, messages
from pro.config import ProConfig
from pro.db import (activity, cases, demo_requests, documents, field_history, fields, firms, invites, items, now,
                    outbox, pages, participant_items, participants, templates, time_entries, usage, users)
from pro.documents import CheckedFile, UploadRejected
from pro.security import check_password, hash_password, new_token, token_hash

SINGLE_VALUE_KEYS = set(extract.FIELD_LABELS) - {"heir"}     # keys where two different values are a conflict


class LimitReached(Exception):
    """Raised with a message for staff when a plan or storage limit stops an action. Nothing is ever charged."""


# ------------------------------------------------------------------ firms, staff, invitations
def create_firm(conn, name: str, owner_email: str, owner_name: str, password: str, plan: str = "pilot",
                is_demo: bool = False, retention_days: int = 365) -> tuple[int, int]:
    firm_id = conn.execute(insert(firms).values(name=name, plan=plan, is_demo=is_demo, retention_days=retention_days,
                                                plan_started_at=now(), created_at=now())).inserted_primary_key[0]
    user_id = conn.execute(insert(users).values(firm_id=firm_id, email=owner_email.lower().strip(), name=owner_name,
                                                password_hash=hash_password(password), role="owner",
                                                created_at=now())).inserted_primary_key[0]
    ensure_templates(conn, firm_id)
    log(conn, firm_id, None, f"user:{user_id}", "firm_created", name)
    return firm_id, user_id


def get_firm(conn, firm_id: int):
    return conn.execute(select(firms).where(firms.c.id == firm_id)).first()


def authenticate(conn, email: str, password: str):
    user = conn.execute(select(users).where(users.c.email == (email or "").lower().strip())).first()
    if user is None or not user.active or not check_password(user.password_hash, password or ""):
        return None
    return user


def get_user(conn, firm_id: int, user_id: int):
    return conn.execute(select(users).where(and_(users.c.id == user_id, users.c.firm_id == firm_id,
                                                 users.c.active.is_(True)))).first()


def staff(conn, firm_id: int):
    return conn.execute(select(users).where(users.c.firm_id == firm_id).order_by(users.c.name)).all()


def email_taken(conn, email: str) -> bool:
    return conn.execute(select(users.c.id).where(users.c.email == email.lower().strip())).first() is not None


def create_invite(conn, firm_id: int, email: str, role: str, by: int, days: int = 7) -> str:
    token = new_token()
    conn.execute(insert(invites).values(firm_id=firm_id, email=email.lower().strip(), role=role,
                                        token_hash=token_hash(token), expires_at=now() + timedelta(days=days),
                                        created_by=by))
    log(conn, firm_id, None, f"user:{by}", "staff_invited", f"{email} as {role}")
    return token


def open_invite(conn, token: str):
    row = conn.execute(select(invites).where(invites.c.token_hash == token_hash(token or ""))).first()
    if row is None or row.used_at is not None or row.expires_at < now():
        return None
    return row


def accept_invite(conn, token: str, name: str, password: str):
    invite = open_invite(conn, token)
    if invite is None or email_taken(conn, invite.email):
        return None
    user_id = conn.execute(insert(users).values(firm_id=invite.firm_id, email=invite.email, name=name,
                                                password_hash=hash_password(password), role=invite.role,
                                                created_at=now())).inserted_primary_key[0]
    conn.execute(update(invites).where(invites.c.id == invite.id).values(used_at=now()))
    log(conn, invite.firm_id, None, f"user:{user_id}", "staff_joined", invite.email)
    return get_user(conn, invite.firm_id, user_id)


def set_staff_active(conn, firm_id: int, user_id: int, active: bool, by: int) -> None:
    conn.execute(update(users).where(and_(users.c.id == user_id, users.c.firm_id == firm_id, users.c.role != "owner"))
                 .values(active=active))
    log(conn, firm_id, None, f"user:{by}", "staff_activated" if active else "staff_deactivated", str(user_id))


# ------------------------------------------------------------------ activity and usage
def log(conn, firm_id: int, case_id: int | None, actor: str, action: str, detail: str = "") -> None:
    # Activity details name documents and fields, never their contents, so the history is not a second copy of them.
    conn.execute(insert(activity).values(firm_id=firm_id, case_id=case_id, actor=actor, action=action,
                                         detail=(detail or "")[:500], created_at=now()))


def case_activity(conn, firm_id: int, case_id: int):
    return conn.execute(select(activity).where(and_(activity.c.firm_id == firm_id, activity.c.case_id == case_id))
                        .order_by(activity.c.created_at, activity.c.id)).all()


def record_usage(conn, firm_id: int, case_id: int | None, kind: str, amount: int) -> None:
    conn.execute(insert(usage).values(firm_id=firm_id, case_id=case_id, kind=kind, amount=amount, created_at=now()))


def usage_totals(conn, firm_id: int, case_id: int | None = None) -> dict[str, int]:
    query = select(usage.c.kind, func.sum(usage.c.amount)).where(usage.c.firm_id == firm_id).group_by(usage.c.kind)
    if case_id is not None:
        query = query.where(usage.c.case_id == case_id)
    return {kind: int(total or 0) for kind, total in conn.execute(query).all()}


# ------------------------------------------------------------------ plan limits
def period_start(firm) -> object:
    plan = billing.plan_for(firm.plan)
    start, length = firm.plan_started_at, timedelta(days=plan.period_days)
    while start + length <= now():
        start += length
    return start


def matters_this_period(conn, firm) -> int:
    return conn.execute(select(func.count()).select_from(cases).where(and_(
        cases.c.firm_id == firm.id, cases.c.counts_toward_plan.is_(True),
        cases.c.created_at >= period_start(firm)))).scalar_one()


TIME_KINDS = {"chasing": "Chasing documents or information", "review": "Reviewing and organizing", "other": "Other"}


def log_time(conn, firm_id: int, case_id: int, user_id: int, minutes: int, kind: str, note: str = "") -> str | None:
    """Staff note how long they spent on a case. Returns a message when it refuses, or None."""
    if get_case(conn, firm_id, case_id) is None:
        return "Case not found."
    if kind not in TIME_KINDS:
        return "Choose what the time was for."
    if not 1 <= minutes <= 600:
        return "Enter between 1 and 600 minutes."
    conn.execute(insert(time_entries).values(firm_id=firm_id, case_id=case_id, user_id=user_id, minutes=minutes,
                                             kind=kind, note=(note or "").strip()[:200] or None, created_at=now()))
    return None


def case_time(conn, firm_id: int, case_id: int):
    return conn.execute(select(time_entries).where(and_(time_entries.c.firm_id == firm_id,
                                                        time_entries.c.case_id == case_id))
                        .order_by(time_entries.c.created_at.desc())).all()


def pilot_measures(conn, firm_id: int) -> dict:
    """Counts for the pilot report, from data HomeKeep already keeps. Staff minutes, the firm's baseline and legal
    outcomes are not measured here: they come from the firm's own time notes (see docs/pro/GO_TO_MARKET.md)."""
    rows = conn.execute(select(cases.c.created_at, cases.c.packet_ready_at).where(cases.c.firm_id == firm_id)).all()
    days = [(r.packet_ready_at - r.created_at).total_seconds() / 86400 for r in rows if r.packet_ready_at]
    actions = dict(conn.execute(select(activity.c.action, func.count()).where(activity.c.firm_id == firm_id)
                                .group_by(activity.c.action)).all())
    uploads = conn.execute(select(documents.c.participant_id).where(documents.c.firm_id == firm_id)).all()
    corrected = actions.get("field_correct", 0)
    reviewed = actions.get("field_approve", 0) + corrected + actions.get("field_reject", 0)
    follow_ups = conn.execute(select(func.count()).select_from(outbox).where(outbox.c.firm_id == firm_id)).scalar()
    minutes = dict(conn.execute(select(time_entries.c.kind, func.sum(time_entries.c.minutes))
                                .where(time_entries.c.firm_id == firm_id).group_by(time_entries.c.kind)).all())
    timed_cases = conn.execute(select(func.count(func.distinct(time_entries.c.case_id)))
                               .where(time_entries.c.firm_id == firm_id)).scalar() or 0
    chasing = int(minutes.get("chasing") or 0)
    return {"minutes_total": int(sum(v or 0 for v in minutes.values())), "minutes_chasing": chasing,
            "timed_cases": timed_cases,
            "chasing_per_case": round(chasing / timed_cases) if timed_cases else None,
            "cases": len(rows), "packets": len(days),
            "median_days_to_packet": round(statistics.median(days), 1) if days else None,
            "family_uploads": sum(1 for u in uploads if u.participant_id),
            "staff_uploads": sum(1 for u in uploads if not u.participant_id),
            "follow_ups": follow_ups, "facts_reviewed": reviewed, "facts_corrected": corrected,
            "correction_rate": round(100 * corrected / reviewed) if reviewed else None}


def firm_storage_bytes(conn, firm_id: int) -> int:
    return int(conn.execute(select(func.coalesce(func.sum(documents.c.size), 0)).where(and_(
        documents.c.firm_id == firm_id, documents.c.deleted_at.is_(None)))).scalar_one())


# ------------------------------------------------------------------ cases and checklist
def create_case(conn, firm_id: int, by: int, reference: str, title: str, decedent: str = "", address: str = "",
                parcel: str = "", assigned_to: int | None = None) -> int:
    firm = get_firm(conn, firm_id)
    plan = billing.plan_for(firm.plan)
    if not firm.is_demo and matters_this_period(conn, firm) >= plan.new_matters:
        raise LimitReached(f"Your {plan.label} includes {plan.new_matters} new matters per period, and they are "
                           "used. Existing cases stay open. Contact HomeKeep to raise the limit; nothing is charged "
                           "automatically.")
    case_id = conn.execute(insert(cases).values(
        firm_id=firm_id, reference=reference.strip()[:80] or "Untitled", title=title.strip()[:200] or "Untitled",
        decedent_name=decedent.strip()[:200] or None, property_address=address.strip()[:300] or None,
        parcel_id=parcel.strip()[:40] or None, assigned_to=assigned_to or by, created_by=by, created_at=now(),
        counts_toward_plan=not firm.is_demo)).inserted_primary_key[0]
    for item in checklist.DEFAULT:
        conn.execute(insert(items).values(firm_id=firm_id, case_id=case_id, key=item.key, label=item.label,
                                          kind=item.kind, required=item.required, status="missing", updated_at=now()))
    log(conn, firm_id, case_id, f"user:{by}", "case_created", reference)
    return case_id


def get_case(conn, firm_id: int, case_id: int):
    return conn.execute(select(cases).where(and_(cases.c.id == case_id, cases.c.firm_id == firm_id))).first()


def list_cases(conn, firm_id: int, include_closed: bool = False):
    query = select(cases).where(cases.c.firm_id == firm_id).order_by(cases.c.created_at.desc())
    if not include_closed:
        query = query.where(cases.c.closed_at.is_(None))
    return conn.execute(query).all()


CASE_STATUSES = {"intake": "Collecting information", "review": "Staff review", "attorney": "Ready for attorney review",
                 "closed": "Closed"}


def update_case(conn, firm_id: int, case_id: int, by: int, **changes) -> None:
    allowed = {k: v for k, v in changes.items() if k in {"status", "assigned_to", "title", "decedent_name",
                                                           "property_address", "parcel_id"}}
    if not allowed or get_case(conn, firm_id, case_id) is None:
        return
    if allowed.get("status") == "closed":
        firm = get_firm(conn, firm_id)
        allowed["closed_at"] = now()
        allowed["delete_after"] = now() + timedelta(days=firm.retention_days)
    elif "status" in allowed:
        allowed["closed_at"], allowed["delete_after"] = None, None
    conn.execute(update(cases).where(and_(cases.c.id == case_id, cases.c.firm_id == firm_id)).values(**allowed))
    log(conn, firm_id, case_id, f"user:{by}", "case_updated", ", ".join(f"{k}={v}" for k, v in changes.items()))


def set_record_source(conn, firm_id: int, case_id: int, by: int, record: dict) -> None:
    conn.execute(update(cases).where(and_(cases.c.id == case_id, cases.c.firm_id == firm_id))
                 .values(record_source=json.dumps(record)))
    log(conn, firm_id, case_id, f"user:{by}", "county_record_attached", record.get("url", ""))


def case_items(conn, firm_id: int, case_id: int):
    return conn.execute(select(items).where(and_(items.c.firm_id == firm_id, items.c.case_id == case_id))
                        .order_by(items.c.id)).all()


def set_item_status(conn, firm_id: int, case_id: int, item_id: int, status: str, actor: str, note: str = "") -> None:
    if status not in checklist.STATUS_LABELS:
        return
    item = conn.execute(select(items).where(and_(items.c.id == item_id, items.c.firm_id == firm_id,
                                                 items.c.case_id == case_id))).first()
    if item is None:
        return
    conn.execute(update(items).where(items.c.id == item_id).values(status=status, note=note[:500] or item.note,
                                                                   updated_at=now()))
    log(conn, firm_id, case_id, actor, "item_status", f"{item.label}: {item.status} -> {status}")


# ------------------------------------------------------------------ family participants
def add_participant(conn, cfg: ProConfig, firm_id: int, case_id: int, by: int, name: str, email: str, relation: str,
                    item_ids: list[int], email_consent: bool) -> str:
    allowed = {i.id for i in case_items(conn, firm_id, case_id) if checklist.BY_KEY.get(i.key, None) is None
               or checklist.BY_KEY[i.key].family_can_provide}
    token = new_token()
    participant_id = conn.execute(insert(participants).values(
        firm_id=firm_id, case_id=case_id, name=name.strip()[:200], email=(email or "").strip()[:254] or None,
        relation=(relation or "").strip()[:80] or None, token_hash=token_hash(token),
        expires_at=now() + timedelta(days=cfg.family_link_days), email_consent=bool(email_consent and email),
        consent_recorded_at=now() if email_consent and email else None,
        consent_recorded_by=by if email_consent and email else None, created_at=now())).inserted_primary_key[0]
    for item_id in item_ids:
        if item_id in allowed:
            conn.execute(insert(participant_items).values(firm_id=firm_id, participant_id=participant_id,
                                                          item_id=item_id))
            set_item_status(conn, firm_id, case_id, item_id, "requested", f"user:{by}")
    log(conn, firm_id, case_id, f"user:{by}", "family_invited", f"{name} ({relation or 'relation not given'})")
    return token


def renew_participant_link(conn, cfg: ProConfig, firm_id: int, case_id: int, participant_id: int, by: int) -> str:
    token = new_token()
    conn.execute(update(participants).where(and_(participants.c.id == participant_id,
                                                 participants.c.firm_id == firm_id,
                                                 participants.c.case_id == case_id))
                 .values(token_hash=token_hash(token), expires_at=now() + timedelta(days=cfg.family_link_days),
                         revoked=False))
    log(conn, firm_id, case_id, f"user:{by}", "family_link_renewed", str(participant_id))
    return token


def revoke_participant(conn, firm_id: int, case_id: int, participant_id: int, by: int) -> None:
    conn.execute(update(participants).where(and_(participants.c.id == participant_id,
                                                 participants.c.firm_id == firm_id,
                                                 participants.c.case_id == case_id)).values(revoked=True))
    log(conn, firm_id, case_id, f"user:{by}", "family_link_revoked", str(participant_id))


def case_participants(conn, firm_id: int, case_id: int):
    return conn.execute(select(participants).where(and_(participants.c.firm_id == firm_id,
                                                        participants.c.case_id == case_id))).all()


def participant_by_token(conn, token: str):
    row = conn.execute(select(participants).where(participants.c.token_hash == token_hash(token or ""))).first()
    if row is None or row.revoked or row.expires_at is None or row.expires_at < now():
        return None
    case = get_case(conn, row.firm_id, row.case_id)
    if case is None or case.closed_at is not None:
        return None
    return row


def participant_requests(conn, participant) -> list:
    """Only the checklist items this person was asked for, never the rest of the case."""
    return conn.execute(select(items).join(participant_items, participant_items.c.item_id == items.c.id).where(and_(
        participant_items.c.participant_id == participant.id, participant_items.c.firm_id == participant.firm_id,
        items.c.firm_id == participant.firm_id, items.c.case_id == participant.case_id))).all()


def participant_uploads(conn, participant):
    return conn.execute(select(documents.c.id, documents.c.filename, documents.c.item_id, documents.c.created_at)
                        .where(and_(documents.c.firm_id == participant.firm_id,
                                    documents.c.participant_id == participant.id,
                                    documents.c.deleted_at.is_(None)))).all()


# ------------------------------------------------------------------ documents
def store_document(conn, cfg: ProConfig, firm_id: int, case_id: int, checked: CheckedFile, *, item_id: int | None,
                   participant_id: int | None = None, uploaded_by: int | None = None) -> int:
    if get_case(conn, firm_id, case_id) is None:
        raise UploadRejected("Case not found.")
    count = conn.execute(select(func.count()).select_from(documents).where(and_(
        documents.c.firm_id == firm_id, documents.c.case_id == case_id, documents.c.deleted_at.is_(None)))).scalar_one()
    if count >= cfg.max_documents_per_case:
        raise UploadRejected("This case already has the most documents it can hold. Please contact the firm.")
    if firm_storage_bytes(conn, firm_id) + len(checked.data) > cfg.max_firm_storage_bytes:
        raise UploadRejected("The firm's storage is full. Please contact the firm.")
    actor = f"participant:{participant_id}" if participant_id else f"user:{uploaded_by}"
    doc_id = conn.execute(insert(documents).values(
        firm_id=firm_id, case_id=case_id, item_id=item_id, participant_id=participant_id, uploaded_by=uploaded_by,
        filename=checked.filename, content_type=checked.content_type, size=len(checked.data), sha256=checked.sha256,
        data=checked.data, status="quarantined", created_at=now())).inserted_primary_key[0]
    log(conn, firm_id, case_id, actor, "document_uploaded", checked.filename)
    if item_id:
        set_item_status(conn, firm_id, case_id, item_id, "received", actor)
    read_document(conn, cfg, firm_id, case_id, doc_id, checked)
    return doc_id


def read_document(conn, cfg: ProConfig, firm_id: int, case_id: int, doc_id: int, checked: CheckedFile) -> None:
    if not checked.is_pdf:
        conn.execute(update(documents).where(documents.c.id == doc_id).values(text_status="not_pdf"))
        return
    result = extract.read_pdf(checked.data, cfg.max_pages_per_document)
    for p in result.pages:
        conn.execute(insert(pages).values(firm_id=firm_id, document_id=doc_id, page=p.page, text=p.text))
    record_usage(conn, firm_id, case_id, "pages_read", len(result.pages))
    values = {"text_status": result.status, "page_count": len(result.pages) or None}
    if result.status == "ok":
        values.update(_propose_from_pages(conn, cfg, firm_id, case_id, doc_id, checked.filename, result.pages))
    else:
        log(conn, firm_id, case_id, "system", "document_unreadable", f"{checked.filename}: {result.status}")
    conn.execute(update(documents).where(documents.c.id == doc_id).values(**values))


def _propose_from_pages(conn, cfg: ProConfig, firm_id: int, case_id: int, doc_id: int, filename: str,
                        page_list: list, note: str = "") -> dict:
    """Suggest facts from a document's text. Every suggestion waits for a person; instruction-like text is flagged."""
    found = extract.run(extract.get_extractor(cfg.extractor), page_list)
    for proposal in found.proposals:
        conn.execute(insert(fields).values(firm_id=firm_id, case_id=case_id, key=proposal.key,
                                           value=proposal.value, source="record", document_id=doc_id,
                                           page=proposal.page, evidence=proposal.evidence,
                                           state="awaiting_review", created_at=now()))
    for warning in found.warnings:
        log(conn, firm_id, case_id, "system", "document_warning", warning)
    log(conn, firm_id, case_id, "system", "document_read",
        f"{filename}: {extract.DOC_TYPES[found.doc_type]}, {len(found.proposals)} fields proposed{note}")
    recheck_conflicts(conn, firm_id, case_id)
    return {"doc_type": found.doc_type, "doc_type_evidence": found.type_evidence}


OCR_MAX_CHARS_PER_PAGE = 20000


def read_ocr_text(conn, cfg: ProConfig, firm_id: int, case_id: int, doc_id: int, by: int,
                  texts: list[str]) -> str | None:
    """Store text that a staff member's own browser read from a scan or photo (Tesseract.js, no outside service),
    then suggest facts from it like any other document. The text is untrusted input, exactly like a PDF's.
    Returns a message for staff when it refuses, or None when the text was stored."""
    doc = get_document(conn, firm_id, case_id, doc_id)
    if doc is None:
        return "Document not found."
    if doc.status != "released":
        return "Release this file before reading it."
    if doc.text_status not in ("no_text", "not_pdf"):
        return "This document's text has already been read."
    texts = [str(t)[:OCR_MAX_CHARS_PER_PAGE] for t in texts[:cfg.max_pages_per_document]]
    if sum(len(t.strip()) for t in texts) < 20:
        return "No readable text was found. Type the facts in by hand on the review page."
    conn.execute(delete(pages).where(and_(pages.c.firm_id == firm_id, pages.c.document_id == doc_id)))
    found_pages = [extract.PageText(i + 1, t.strip()) for i, t in enumerate(texts)]
    for p in found_pages:
        conn.execute(insert(pages).values(firm_id=firm_id, document_id=doc_id, page=p.page, text=p.text))
    record_usage(conn, firm_id, case_id, "pages_ocr", len(found_pages))
    log(conn, firm_id, case_id, f"user:{by}", "document_ocr", doc.filename)
    values = {"text_status": "ocr", "page_count": len(found_pages)}
    values.update(_propose_from_pages(conn, cfg, firm_id, case_id, doc_id, doc.filename, found_pages,
                                      " (read from an image by OCR; check each value against the file)"))
    conn.execute(update(documents).where(documents.c.id == doc_id).values(**values))
    return None


def list_documents(conn, firm_id: int, case_id: int, include_deleted: bool = False):
    columns = [c for c in documents.c if c.name != "data"]
    query = select(*columns).where(and_(documents.c.firm_id == firm_id, documents.c.case_id == case_id))
    if not include_deleted:
        query = query.where(documents.c.deleted_at.is_(None))
    return conn.execute(query.order_by(documents.c.created_at)).all()


def get_document(conn, firm_id: int, case_id: int, doc_id: int):
    return conn.execute(select(documents).where(and_(documents.c.id == doc_id, documents.c.firm_id == firm_id,
                                                     documents.c.case_id == case_id,
                                                     documents.c.deleted_at.is_(None)))).first()


def document_pages(conn, firm_id: int, doc_id: int):
    return conn.execute(select(pages).where(and_(pages.c.firm_id == firm_id, pages.c.document_id == doc_id))
                        .order_by(pages.c.page)).all()


def release_document(conn, firm_id: int, case_id: int, doc_id: int, by: int) -> None:
    conn.execute(update(documents).where(and_(documents.c.id == doc_id, documents.c.firm_id == firm_id,
                                              documents.c.case_id == case_id, documents.c.status == "quarantined"))
                 .values(status="released"))
    log(conn, firm_id, case_id, f"user:{by}", "document_released", str(doc_id))


def delete_document(conn, firm_id: int, case_id: int, doc_id: int, by: int, reason: str) -> None:
    doc = get_document(conn, firm_id, case_id, doc_id)
    if doc is None:
        return
    conn.execute(update(documents).where(documents.c.id == doc_id)
                 .values(data=None, status="deleted", deleted_at=now()))
    conn.execute(delete(pages).where(and_(pages.c.firm_id == firm_id, pages.c.document_id == doc_id)))
    # Unreviewed proposals from the deleted file go too; approved values stay, with the deletion in their history.
    conn.execute(delete(fields).where(and_(fields.c.firm_id == firm_id, fields.c.document_id == doc_id,
                                           fields.c.state != "approved")))
    for kept in conn.execute(select(fields).where(and_(fields.c.firm_id == firm_id, fields.c.document_id == doc_id))):
        conn.execute(insert(field_history).values(firm_id=firm_id, field_id=kept.id, old_value=kept.value,
                                                  new_value=kept.value, old_state=kept.state, new_state=kept.state,
                                                  changed_by=by, reason="Source document deleted", changed_at=now()))
    log(conn, firm_id, case_id, f"user:{by}", "document_deleted", f"{doc.filename}: {reason[:200]}")
    recheck_conflicts(conn, firm_id, case_id)


# ------------------------------------------------------------------ fields and review
def case_fields(conn, firm_id: int, case_id: int):
    return conn.execute(select(fields).where(and_(fields.c.firm_id == firm_id, fields.c.case_id == case_id))
                        .order_by(fields.c.key, fields.c.id)).all()


def add_field(conn, firm_id: int, case_id: int, key: str, value: str, source: str, actor: str,
              reported_by: int | None = None, evidence: str = "") -> int | None:
    if key not in extract.FIELD_LABELS or not (value or "").strip():
        return None
    field_id = conn.execute(insert(fields).values(
        firm_id=firm_id, case_id=case_id, key=key, value=value.strip()[:extract.MAX_VALUE], source=source,
        reported_by=reported_by, evidence=evidence[:300] or None,
        state="approved" if source == "staff" else "awaiting_review",
        reviewed_at=now() if source == "staff" else None, created_at=now())).inserted_primary_key[0]
    log(conn, firm_id, case_id, actor, "field_added", f"{extract.FIELD_LABELS[key]} ({source})")
    recheck_conflicts(conn, firm_id, case_id)
    return field_id


def review_field(conn, firm_id: int, case_id: int, field_id: int, by: int, action: str, new_value: str = "",
                 reason: str = "") -> None:
    field = conn.execute(select(fields).where(and_(fields.c.id == field_id, fields.c.firm_id == firm_id,
                                                   fields.c.case_id == case_id))).first()
    if field is None:
        return
    value, state = field.value, field.state
    if action == "approve":
        state = "approved"
    elif action == "correct" and new_value.strip():
        value, state = new_value.strip()[:extract.MAX_VALUE], "approved"
    elif action == "reject":
        state = "rejected"
    else:
        return
    conn.execute(update(fields).where(fields.c.id == field_id)
                 .values(value=value, state=state, reviewed_by=by, reviewed_at=now()))
    conn.execute(insert(field_history).values(firm_id=firm_id, field_id=field_id, old_value=field.value,
                                              new_value=value, old_state=field.state, new_state=state,
                                              changed_by=by, reason=reason[:500] or None, changed_at=now()))
    if state == "approved" and field.key in SINGLE_VALUE_KEYS:
        # Other open values for the same fact are set aside, not deleted, so the history still shows them.
        conn.execute(update(fields).where(and_(fields.c.firm_id == firm_id, fields.c.case_id == case_id,
                                               fields.c.key == field.key, fields.c.id != field_id,
                                               fields.c.state.in_(("awaiting_review", "conflicting"))))
                     .values(state="set_aside"))
    log(conn, firm_id, case_id, f"user:{by}", f"field_{action}", extract.FIELD_LABELS[field.key])
    recheck_conflicts(conn, firm_id, case_id)


def field_history_for(conn, firm_id: int, field_id: int):
    return conn.execute(select(field_history).where(and_(field_history.c.firm_id == firm_id,
                                                         field_history.c.field_id == field_id))
                        .order_by(field_history.c.changed_at, field_history.c.id)).all()


def recheck_conflicts(conn, firm_id: int, case_id: int) -> None:
    """Two different open values for the same fact are both marked conflicting until a person resolves them."""
    rows = [f for f in case_fields(conn, firm_id, case_id)
            if f.key in SINGLE_VALUE_KEYS and f.state in ("awaiting_review", "conflicting", "approved")]
    by_key: dict[str, list] = {}
    for f in rows:
        by_key.setdefault(f.key, []).append(f)
    for key, group in by_key.items():
        distinct = {extract.normalize(f.value) for f in group}
        approved = [f for f in group if f.state == "approved"]
        for f in group:
            if f.state == "approved":
                continue
            conflicting = len(distinct) > 1 and not (approved and extract.normalize(f.value) ==
                                                     extract.normalize(approved[-1].value))
            state = "conflicting" if conflicting else "awaiting_review"
            if state != f.state:
                conn.execute(update(fields).where(fields.c.id == f.id).values(state=state))


def fact_summary(conn, firm_id: int, case_id: int) -> list[dict]:
    """One row per fact: approved value, open values, or Missing. Used by the review screen and the packet."""
    rows = case_fields(conn, firm_id, case_id)
    summary = []
    for key, label in extract.FIELD_LABELS.items():
        found = [f for f in rows if f.key == key and f.state not in ("rejected", "set_aside")]
        if not found:
            state = "missing"
        elif any(f.state == "conflicting" for f in found):
            state = "conflicting"
        elif all(f.state == "approved" for f in found):
            state = "approved"
        else:
            state = "awaiting_review"
        summary.append({"key": key, "label": label, "state": state, "fields": found})
    return summary


# ------------------------------------------------------------------ message templates and follow-ups
def ensure_templates(conn, firm_id: int) -> None:
    if conn.execute(select(templates.c.id).where(templates.c.firm_id == firm_id)).first() is None:
        for name, subject, body in messages.DEFAULT_TEMPLATES:
            conn.execute(insert(templates).values(firm_id=firm_id, name=name, subject=subject, body=body))


def firm_templates(conn, firm_id: int):
    return conn.execute(select(templates).where(templates.c.firm_id == firm_id).order_by(templates.c.id)).all()


def save_template(conn, firm_id: int, template_id: int, by: int, subject: str, body: str) -> str | None:
    unknown = messages.unknown_placeholders(subject + body)
    if unknown:
        return "Unknown placeholders: " + ", ".join(sorted(unknown))
    conn.execute(update(templates).where(and_(templates.c.id == template_id, templates.c.firm_id == firm_id))
                 .values(subject=subject[:200], body=body[:5000], approved_by=None, approved_at=None))
    log(conn, firm_id, None, f"user:{by}", "template_edited", str(template_id))
    return None


def approve_template(conn, firm_id: int, template_id: int, by: int) -> None:
    conn.execute(update(templates).where(and_(templates.c.id == template_id, templates.c.firm_id == firm_id))
                 .values(approved_by=by, approved_at=now()))
    log(conn, firm_id, None, f"user:{by}", "template_approved", str(template_id))


def send_follow_up(conn, cfg: ProConfig, firm_id: int, case_id: int, participant_id: int, template_id: int, by: int,
                   link: str) -> tuple[bool, str]:
    case = get_case(conn, firm_id, case_id)
    person = conn.execute(select(participants).where(and_(participants.c.id == participant_id,
                                                          participants.c.firm_id == firm_id,
                                                          participants.c.case_id == case_id))).first()
    template = conn.execute(select(templates).where(and_(templates.c.id == template_id,
                                                         templates.c.firm_id == firm_id))).first()
    if case is None or person is None or template is None:
        return False, "Not found."
    if template.approved_at is None:
        return False, "An attorney or owner must approve this template before it can be used."
    if not person.email or not person.email_consent:
        return False, f"{person.name} has not agreed to email. Record their consent first, or contact them another way."
    since = now() - timedelta(hours=cfg.duplicate_message_hours)
    recent = conn.execute(select(outbox.c.id).where(and_(outbox.c.firm_id == firm_id,
                                                         outbox.c.participant_id == participant_id,
                                                         outbox.c.template_id == template_id,
                                                         outbox.c.created_at >= since))).first()
    if recent is not None:
        return False, f"This message already went to {person.name} in the last {cfg.duplicate_message_hours} hours."
    missing = [i.label for i in participant_requests(conn, person) if i.status in ("missing", "requested")]
    values = {"name": person.name, "case_title": case.title, "firm_name": get_firm(conn, firm_id).name,
              "missing_list": "\n".join(f"- {m}" for m in missing) or "- Nothing right now",
              "link": link, "link_expires": f"{person.expires_at:%B %d, %Y}"}
    conn.execute(insert(outbox).values(firm_id=firm_id, case_id=case_id, participant_id=participant_id,
                                       template_id=template_id, to_email=person.email,
                                       subject=messages.render(template.subject, values),
                                       body=messages.render(template.body, values),
                                       status="recorded" if cfg.email_mode == "outbox" else "sent",
                                       created_by=by, created_at=now()))
    log(conn, firm_id, case_id, f"user:{by}", "follow_up_prepared", f"{template.name} to {person.name}")
    if cfg.email_mode == "outbox":
        return True, (f"Message ready for {person.name}. In the outbox below, open it in your own email, send it, "
                      "then mark it sent.")
    return True, f"Message sent to {person.name}."


def case_outbox(conn, firm_id: int, case_id: int):
    return conn.execute(select(outbox).where(and_(outbox.c.firm_id == firm_id, outbox.c.case_id == case_id))
                        .order_by(outbox.c.created_at.desc())).all()


def mark_outbox_sent(conn, firm_id: int, case_id: int, message_id: int, by: int) -> bool:
    """Staff sent a prepared message from their own email program. HomeKeep can't see that, so a person confirms it."""
    message = conn.execute(select(outbox).where(and_(outbox.c.id == message_id, outbox.c.firm_id == firm_id,
                                                     outbox.c.case_id == case_id))).first()
    if message is None or message.status != "recorded":
        return False
    conn.execute(update(outbox).where(outbox.c.id == message_id).values(status="sent_by_staff"))
    log(conn, firm_id, case_id, f"user:{by}", "follow_up_sent", f"{message.subject} to {message.to_email}")
    return True


def record_consent(conn, firm_id: int, case_id: int, participant_id: int, by: int, agreed: bool) -> None:
    conn.execute(update(participants).where(and_(participants.c.id == participant_id, participants.c.firm_id == firm_id,
                                                 participants.c.case_id == case_id))
                 .values(email_consent=agreed, consent_recorded_at=now(), consent_recorded_by=by))
    log(conn, firm_id, case_id, f"user:{by}", "consent_recorded", f"participant {participant_id}: {agreed}")


# ------------------------------------------------------------------ settings, retention and deletion
def set_retention(conn, firm_id: int, days: int, by: int) -> None:
    days = max(30, min(days, 3650))
    conn.execute(update(firms).where(firms.c.id == firm_id).values(retention_days=days))
    log(conn, firm_id, None, f"user:{by}", "retention_changed", f"{days} days")


def approve_checklist(conn, firm_id: int, by: int) -> None:
    conn.execute(update(firms).where(firms.c.id == firm_id).values(checklist_approved_by=by,
                                                                   checklist_approved_at=now()))
    log(conn, firm_id, None, f"user:{by}", "checklist_approved", "default intake checklist")


def delete_case(conn, firm_id: int, case_id: int, actor: str) -> None:
    """Removes the case and everything in it. Only a short note stays in the firm's activity log."""
    case = get_case(conn, firm_id, case_id)
    if case is None:
        return
    field_ids = [f.id for f in case_fields(conn, firm_id, case_id)]
    doc_ids = [d.id for d in list_documents(conn, firm_id, case_id, include_deleted=True)]
    person_ids = [p.id for p in case_participants(conn, firm_id, case_id)]
    if field_ids:
        conn.execute(delete(field_history).where(and_(field_history.c.firm_id == firm_id,
                                                      field_history.c.field_id.in_(field_ids))))
    if doc_ids:
        conn.execute(delete(pages).where(and_(pages.c.firm_id == firm_id, pages.c.document_id.in_(doc_ids))))
    if person_ids:
        conn.execute(delete(participant_items).where(and_(participant_items.c.firm_id == firm_id,
                                                          participant_items.c.participant_id.in_(person_ids))))
    for table in (fields, documents, outbox, participants, items, usage, time_entries, activity):
        conn.execute(delete(table).where(and_(table.c.firm_id == firm_id, table.c.case_id == case_id)))
    conn.execute(delete(cases).where(and_(cases.c.id == case_id, cases.c.firm_id == firm_id)))
    log(conn, firm_id, None, actor, "case_deleted", f"case {case.reference}")


def purge_expired(conn) -> int:
    """Deletes closed cases past their firm's retention date. Safe to run on a schedule."""
    due = conn.execute(select(cases.c.id, cases.c.firm_id).where(and_(cases.c.delete_after.is_not(None),
                                                                      cases.c.delete_after < now()))).all()
    for case_id, firm_id in due:
        delete_case(conn, firm_id, case_id, "system")
    return len(due)


def save_demo_request(conn, name: str, firm: str, email: str, role: str, message: str, consent: bool) -> None:
    conn.execute(insert(demo_requests).values(name=name[:200], firm=firm[:200], email=email[:254], role=role[:120],
                                              message=message[:2000], consent=consent, created_at=now()))
