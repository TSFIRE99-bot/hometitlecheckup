"""Translations: English, Spanish (Español) and Somali (Soomaali).

Every sentence the app shows is written in English in the code and passed through t(). t() looks it up in the
catalog for the current language (titlecheck/locale/es.py or so.py) and fills in the {placeholders}:

    t("There are {n} owners on the record.", n=3)

N_() marks English text that is stored in a list or table and translated later with t(); it changes nothing by
itself. The language is set once per page request (web/__init__.py), from the language the visitor picked.
If a sentence has no translation yet, the English is shown, so the app never breaks.
"""
from __future__ import annotations

from contextvars import ContextVar

LANGS = {"en": "English", "es": "Español", "so": "Soomaali"}
DEFAULT = "en"

_lang: ContextVar[str] = ContextVar("lang", default=DEFAULT)
MISSING: set[tuple[str, str]] = set()        # (language, English text) with no translation; tests check it stays empty


def _catalogs() -> dict[str, dict[str, str]]:
    from titlecheck.locale import es, so
    return {"es": es.T, "so": so.T}


_CATALOGS: dict[str, dict[str, str]] | None = None


def set_lang(code: str | None) -> str:
    code = code if code in LANGS else DEFAULT
    _lang.set(code)
    return code


def get_lang() -> str:
    return _lang.get()


def N_(text: str) -> str:
    return text


MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
           "noviembre", "diciembre"],
    "so": ["Janaayo", "Febraayo", "Maarso", "Abriil", "May", "Juun", "Luuliyo", "Ogost", "Sebtembar", "Oktoobar",
           "Nofembar", "Desembar"],
}


def format_date(d) -> str:
    """'October 24, 2026' / '24 de octubre de 2026' / '24 Oktoobar 2026'."""
    lang = _lang.get()
    month = MONTHS[lang][d.month - 1]
    if lang == "es":
        return f"{d.day} de {month} de {d.year}"
    if lang == "so":
        return f"{d.day} {month} {d.year}"
    return f"{month} {d.day}, {d.year}"


def t(text: str, **values) -> str:
    global _CATALOGS
    lang = _lang.get()
    out = text
    if lang != DEFAULT and text:
        if _CATALOGS is None:
            _CATALOGS = _catalogs()
        found = _CATALOGS.get(lang, {}).get(text)
        if found is None:
            MISSING.add((lang, text))
        else:
            out = found
    return out.format(**values) if values else out
