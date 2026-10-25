"""Reads the editable page text in content/*.md, so the About and Learn pages can be changed without touching code.

The files use a tiny, forgiving bit of Markdown:

    # Page title
    Text before the first section is the page's introduction.

    ## Section heading {icon}     <- every "##" starts a new card; {icon} is optional (see _icons.html for names)
    A paragraph. Blank lines separate paragraphs.
    - a bullet point
    1. a numbered point
    ### A smaller heading
    **bold**, *italic* and [a link](https://example.org) work anywhere.
    <!-- anything between these marks is a note to yourself and never shows on the site -->

Everything is escaped first, so nothing typed in the files can turn into HTML or scripts.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from markupsafe import Markup

from web.markup import md

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
COMMENT = re.compile(r"<!--.*?-->", re.S)
ICON_TAG = re.compile(r"\s*\{(\w+)\}\s*$")
BULLET = re.compile(r"^\s*[-*]\s+")
NUMBER = re.compile(r"^\s*\d+[.)]\s+")


@dataclass
class Section:
    title: str
    html: Markup
    icon: str = ""


@dataclass
class Page:
    title: str = ""
    intro: Markup = field(default_factory=lambda: Markup(""))
    sections: list[Section] = field(default_factory=list)

    def section(self, title: str) -> Section | None:
        return next((s for s in self.sections if s.title.lower() == title.lower()), None)


def _list(lines: list[str], marker: re.Pattern, tag: str) -> str:
    items: list[str] = []
    for line in lines:
        if marker.match(line):
            items.append(marker.sub("", line))
        elif items:
            items[-1] += " " + line.strip()           # a line that continues the item above
    return f"<{tag}>" + "".join(f"<li>{md(i)}</li>" for i in items) + f"</{tag}>"


def blocks_to_html(text: str) -> Markup:
    """Paragraphs, bullet lists, numbered lists and ### headings."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if lines[0].startswith("### "):
            out.append(f"<h3>{md(lines[0][4:].strip())}</h3>")
            lines = lines[1:]
            if not lines:
                continue
        if BULLET.match(lines[0]):
            out.append(_list(lines, BULLET, "ul"))
        elif NUMBER.match(lines[0]):
            out.append(_list(lines, NUMBER, "ol"))
        else:
            out.append(f"<p>{md(' '.join(line.strip() for line in lines))}</p>")
    return Markup("".join(out))


def parse(text: str) -> Page:
    text = COMMENT.sub("", text)
    page, intro, current, body = Page(), [], None, []

    def close():
        if current is not None:
            title, icon = current
            page.sections.append(Section(title, blocks_to_html("\n".join(body)), icon))

    for line in text.splitlines():
        if line.startswith("## "):
            close()
            heading = line[3:].strip()
            tag = ICON_TAG.search(heading)
            current, body = (ICON_TAG.sub("", heading), tag.group(1) if tag else ""), []
        elif line.startswith("# ") and current is None and not page.title:
            page.title = line[2:].strip()
        elif current is None:
            intro.append(line)
        else:
            body.append(line)
    close()
    page.intro = blocks_to_html("\n".join(intro))
    return page


def load(name: str) -> Page:
    """content/<name>.md, read fresh each time so an edit shows up on the next page load."""
    return parse((CONTENT_DIR / f"{name}.md").read_text(encoding="utf-8"))
