"""Printable one-page action plan (PDF), so a family can take it to the Recorder or Legal Aid."""
from __future__ import annotations

import re
from datetime import date

from fpdf import FPDF

from titlecheck.assess import Assessment

MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def plain(text: str) -> str:
    """Markdown -> plain text that the PDF's built-in font can print."""
    text = MD_LINK.sub(r"\1 (\2)", text)
    text = text.replace("**", "")
    text = (text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
            .replace("–", "-").replace("—", "-"))
    return text.encode("latin-1", "replace").decode("latin-1")


def build_pdf(result: Assessment, address: str | None, notes: list[str], details: list[str] | None = None) -> bytes:
    pdf = FPDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Home Title Checkup: my action plan", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, plain(f"Home: {address or 'not looked up'}    Date: {date.today():%B %d, %Y}"),
             new_x="LMARGIN", new_y="NEXT")
    for line in details or []:
        pdf.cell(0, 6, plain(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, plain(f"Result: {result.label}. {result.headline}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for line in result.reasons + notes:
        pdf.multi_cell(0, 6, plain(f"- {line}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Steps", new_x="LMARGIN", new_y="NEXT")
    for i, step in enumerate(result.steps, 1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, plain(f"[  ]  {i}. {step.title}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, plain(step.detail), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, "General information about Ohio law, not legal advice. Laws, forms and fees change; "
                         "confirm with the County offices or a lawyer before filing anything.",
                   new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
