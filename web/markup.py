"""Turns the little bit of Markdown the rules use (**bold** and [links](url)) into safe HTML."""
from __future__ import annotations

import re

from markupsafe import Markup, escape

BOLD = re.compile(r"\*\*(.+?)\*\*")
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def md(text: str) -> Markup:
    """Escape everything first, so County data and typed names can never become HTML, then add bold and links."""
    html = str(escape(text))
    html = LINK.sub(r'<a href="\2" target="_blank" rel="noopener">\1</a>', html)
    html = BOLD.sub(r"<strong>\1</strong>", html)
    return Markup(html)
