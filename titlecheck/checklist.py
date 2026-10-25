"""Printable one-page action plan (PDF), so a family can take it to the Recorder or Legal Aid."""
from __future__ import annotations

import re
from datetime import date

from fpdf import FPDF

from titlecheck.assess import Assessment
from titlecheck.i18n import format_date, t
from titlecheck.homestead import HomesteadPlan

MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def plain(text: str) -> str:
    """Markdown -> plain text that the PDF's built-in font can print."""
    text = MD_LINK.sub(r"\1 (\2)", text)
    text = text.replace("**", "")
    text = (text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
            .replace("–", "-").replace("—", "-"))
    return text.encode("latin-1", "replace").decode("latin-1")


def _step_facts(step, places: dict[str, str] | None) -> str:
    """'Time: About 30 minutes  |  Cost: Free form  |  Where: Franklin County Law Library'."""
    facts = [(t("Time"), step.time), (t("Cost"), step.cost), (t("Where"), (places or {}).get(step.where, ""))]
    return "  |  ".join(f"{k}: {v}" for k, v in facts if v)


def _header(pdf: FPDF, title: str, address: str | None, prepared_for: str = "") -> None:
    pdf.set_fill_color(19, 49, 92)
    pdf.rect(0, 0, 216, 6, style="F")
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, plain(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    if prepared_for:
        pdf.cell(0, 6, plain(t("Prepared for {name}", name=prepared_for)), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, plain(t("Home: {address}    Date: {date}", address=address or t("not looked up"), date=format_date(date.today()))),
             new_x="LMARGIN", new_y="NEXT")


def build_pdf(result: Assessment, address: str | None, notes: list[str], details: list[str] | None = None,
              prepared_for: str = "", summary: str = "", places: dict[str, str] | None = None) -> bytes:
    pdf = FPDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _header(pdf, t("HomeKeep: my action plan"), address, prepared_for)
    for line in details or []:
        pdf.cell(0, 6, plain(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, plain(t("Result: {label}. {headline}", label=result.label, headline=result.headline)), new_x="LMARGIN", new_y="NEXT")
    if summary:
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 6, plain(summary), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for line in result.reasons + notes:
        pdf.multi_cell(0, 6, plain(f"- {line}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, plain(t("My roadmap: check off each step")), new_x="LMARGIN", new_y="NEXT")
    for i, step in enumerate(result.steps, 1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, plain(f"[  ]  {i}. {step.title}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, plain(step.detail), new_x="LMARGIN", new_y="NEXT")
        facts = _step_facts(step, places)
        if facts:
            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 5, plain(facts), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, plain(t("General information about Ohio law, not legal advice. Laws, forms and fees change; "
                                 "confirm with the County offices or a lawyer before filing anything.")),
                   new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def build_homestead_pdf(plan: HomesteadPlan, address: str | None, prepared_for: str = "") -> bytes:
    """One-page Homestead Benefits checklist, to take to the County Auditor."""
    pdf = FPDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _header(pdf, t("HomeKeep: homestead benefits checklist"), address, prepared_for)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, plain(plan.headline), new_x="LMARGIN", new_y="NEXT")
    if plan.savings:
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, plain(t("Estimated savings: about ${amount} a year.", amount=f"{plan.savings.yearly:,}") + " " + plan.savings.source),
                       new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for line in plan.notes:
        pdf.multi_cell(0, 6, plain(f"- {line}"), new_x="LMARGIN", new_y="NEXT")
    if plan.timeline:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, plain(t("When it happens")), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        for when, what in plan.timeline:
            pdf.multi_cell(0, 6, plain(f"{when}: {what}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    for i, step in enumerate(plan.steps, 1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, plain(f"[  ]  {i}. {step.title}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, plain(step.detail), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, plain(t("Good to know")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 10)
    for line in plan.caveats:
        pdf.multi_cell(0, 5, plain(f"- {line}"), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
