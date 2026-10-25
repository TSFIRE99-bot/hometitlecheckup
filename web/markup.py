"""Turns the little bit of Markdown the rules use (**bold** and [links](url)) into safe HTML."""
from __future__ import annotations

import re

from markupsafe import Markup, escape

BOLD = re.compile(r"\*\*(.+?)\*\*")
ITALIC = re.compile(r"(?<![*\w])\*(?!\s)([^*]+?)\*(?![*\w])")
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
PAGE_LINK = re.compile(r"\[([^\]]+)\]\((/[\w\-/#]*)\)")


def md(text: str) -> Markup:
    """Escape everything first, so County data and typed names can never become HTML, then add bold and links."""
    html = str(escape(text))
    html = LINK.sub(r'<a href="\2" target="_blank" rel="noopener">\1</a>', html)
    html = PAGE_LINK.sub(r'<a href="\2">\1</a>', html)          # links to the app's own pages, like (/inherit)
    html = BOLD.sub(r"<strong>\1</strong>", html)
    html = ITALIC.sub(r"<em>\1</em>", html)
    return Markup(html)
