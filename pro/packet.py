"""The case packet: what a reviewing attorney gets, as a PDF and as JSON for the firm's own systems.

It says what was collected and what is still open. It is not a legal conclusion, a title opinion, or a determination
of heirs, and every page says so. Producing a packet marks the case "packet ready", which is tracked separately from
any legal outcome.
"""
from __future__ import annotations

import json
import re
from datetime import date

from fpdf import FPDF

from pro import checklist, extract, store
from titlecheck.checklist import plain

NOTICE = ("Prepared for professional review. This packet organizes information collected from family members and "
          "documents. It is not legal advice, a title opinion, or a determination of heirs or ownership. Values marked "
          "approved were confirmed by firm staff; everything else still needs review.")

SOURCE_LABELS = {"family": "Reported by family", "record": "Appears in a document", "staff": "Entered by staff"}
STATE_LABELS = {"approved": "Approved by staff", "awaiting_review": "Awaiting review", "conflicting": "Conflicting",
                "missing": "Missing", "rejected": "Rejected", "set_aside": "Set aside"}


def gather(conn, firm_id: int, case_id: int) -> dict:
    case = store.get_case(conn, firm_id, case_id)
    firm = store.get_firm(conn, firm_id)
    docs = store.list_documents(conn, firm_id, case_id)
    doc_names = {d.id: d.filename for d in docs}
    item_rows = store.case_items(conn, firm_id, case_id)
    facts = []
    for fact in store.fact_summary(conn, firm_id, case_id):
        facts.append({"key": fact["key"], "label": fact["label"], "state": fact["state"],
                      "values": [{"value": f.value, "state": f.state, "source": f.source,
                                  "document": doc_names.get(f.document_id), "page": f.page, "evidence": f.evidence}
                                 for f in fact["fields"]]})
    return {
        "notice": NOTICE,
        "firm": firm.name,
        "checklist_status": ("Approved by the firm" if firm.checklist_approved_at else
                             "Draft: awaiting professional approval"),
        "case": {"reference": case.reference, "title": case.title, "status": store.CASE_STATUSES.get(case.status),
                 "decedent_as_entered": case.decedent_name, "property_address_as_entered": case.property_address,
                 "parcel_id_as_entered": case.parcel_id, "county": case.county,
                 "county_record": json.loads(case.record_source) if case.record_source else None},
        "documents": [{"file": d.filename, "type": extract.DOC_TYPES.get(d.doc_type or "", "Not identified"),
                       "pages": d.page_count, "readable": d.text_status, "sha256": d.sha256,
                       "uploaded": f"{d.created_at:%Y-%m-%d}", "status": d.status} for d in docs],
        "facts": facts,
        "missing_items": [i.label for i in checklist.outstanding(item_rows)],
        "checklist": [{"item": i.label, "required": i.required, "status": checklist.STATUS_LABELS[i.status]}
                      for i in item_rows],
        "prepared": f"{date.today():%Y-%m-%d}",
    }


LINK_CODE = re.compile(r"/f/[A-Za-z0-9_\-]+")


def firm_export(conn, firm_id: int) -> dict:
    """Everything the firm has typed or approved, for every case, in one file. Document files stay downloadable one
    at a time from each case: together they can be far larger than one download from this hosting allows."""
    firm = store.get_firm(conn, firm_id)
    people = {u.id: u.name for u in store.staff(conn, firm_id)}
    exported = []
    for c in store.list_cases(conn, firm_id, include_closed=True):
        data = gather(conn, firm_id, c.id)
        data["time_spent"] = [{"when": t.created_at, "who": people.get(t.user_id, "staff"), "minutes": t.minutes,
                               "for": store.TIME_KINDS.get(t.kind, t.kind), "note": t.note}
                              for t in store.case_time(conn, firm_id, c.id)]
        data["family"] = [{"name": p.name, "relation": p.relation, "email": p.email,
                           "agreed_to_email": bool(p.email_consent), "link_expires": p.expires_at,
                           "link_revoked": bool(p.revoked)} for p in store.case_participants(conn, firm_id, c.id)]
        # message bodies carry each relative's private link; a copy of the data must not carry working links
        data["messages"] = [{"prepared": m.created_at, "to": m.to_email, "subject": m.subject,
                             "body": LINK_CODE.sub("/f/[link removed]", m.body), "status": m.status}
                            for m in store.case_outbox(conn, firm_id, c.id)]
        data["history"] = [{"when": a.created_at, "who": a.actor, "what": a.action, "detail": a.detail}
                           for a in store.case_activity(conn, firm_id, c.id)]
        exported.append(data)
    return {"firm": firm.name, "notice": NOTICE, "staff": [{"name": u.name, "email": u.email, "role": u.role}
                                                          for u in store.staff(conn, firm_id)],
            "cases": exported}


def as_json(data: dict) -> bytes:
    return json.dumps(data, indent=2, default=str).encode()


def as_pdf(data: dict) -> bytes:
    pdf = FPDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def heading(text: str, size: int = 13):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", size)
        pdf.multi_cell(0, 7, plain(text), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)

    def line(text: str, style: str = ""):
        pdf.set_font("Helvetica", style, 10)
        pdf.multi_cell(0, 5, plain(text), new_x="LMARGIN", new_y="NEXT")

    case = data["case"]
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 8, plain(f"Case packet: {case['title']}"), new_x="LMARGIN", new_y="NEXT")
    line(f"{data['firm']} | Matter {case['reference']} | Prepared {data['prepared']}")
    pdf.set_fill_color(253, 244, 230)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, plain(NOTICE), fill=True, new_x="LMARGIN", new_y="NEXT")

    heading("Summary")
    line(f"Status: {case['status']}. Checklist: {data['checklist_status']}.")
    line(f"Entered by staff: person who died {case['decedent_as_entered'] or 'not entered'}; property "
         f"{case['property_address_as_entered'] or 'not entered'}; parcel {case['parcel_id_as_entered'] or 'not entered'}.")
    record = case.get("county_record")
    if record:
        line(f"County record: {record.get('url')} (retrieved {record.get('retrieved')}). {record.get('limits')}")
    open_count = sum(1 for f in data["facts"] if f["state"] in ("conflicting", "awaiting_review"))
    line(f"{len(data['documents'])} documents, {len(data['missing_items'])} required items missing, "
         f"{open_count} facts still open.", "B")

    heading("Missing items")
    for item in data["missing_items"] or ["None"]:
        line(f"[  ] {item}")

    heading("Facts")
    for fact in data["facts"]:
        if fact["state"] == "missing":
            continue
        line(f"{fact['label']}: {STATE_LABELS[fact['state']]}", "B")
        for v in fact["values"]:
            where = f"{v['document']}, page {v['page']}" if v["document"] else SOURCE_LABELS[v["source"]]
            line(f"  {v['value']}  ({STATE_LABELS.get(v['state'], v['state'])}; {SOURCE_LABELS[v['source']]}; {where})")
            if v["evidence"]:
                line(f"    Evidence: \"{v['evidence']}\"", "I")
    missing_facts = [f["label"] for f in data["facts"] if f["state"] == "missing"]
    if missing_facts:
        line("Not found yet: " + "; ".join(missing_facts), "I")

    heading("Document inventory")
    for d in data["documents"] or [{"file": "No documents", "type": "", "pages": None, "readable": "", "sha256": "",
                                    "uploaded": "", "status": ""}]:
        line(f"{d['file']} | {d['type']} | {d['pages'] or '?'} pages | text: {d['readable']} | uploaded {d['uploaded']}"
             f" | {d['status']}" + (f" | sha256 {d['sha256'][:12]}" if d["sha256"] else ""))

    heading("Checklist")
    for item in data["checklist"]:
        line(f"{'Required' if item['required'] else 'If applicable'}: {item['item']} - {item['status']}")
    return bytes(pdf.output())
