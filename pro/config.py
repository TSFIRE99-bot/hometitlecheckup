"""Settings for HomeKeep Pro, read from environment variables. Secrets are never given defaults that ship to production.

Environment variables (names only; values live in the hosting dashboard, never in the repository):

    PRO_DATABASE_URL     SQLAlchemy URL. Default: SQLite in a local folder, or in /tmp on Vercel (resets on cold start).
    SECRET_KEY           Signs sign-in sessions. Without it each server instance makes a random key, so sign-ins reset.
    PRO_SIGNUP           "1" lets anyone create a firm account (staging only). Default: off.
    PRO_DEMO             "1" creates the fictional demo firm and shows the "Try the demo" button. Default: on.
    PRO_EXTRACTOR        "rules" (default, offline). A hosted-model adapter can be added later; see pro/extract.py.
    PRO_EMAIL            "outbox" (default): messages are recorded but never leave the app.
    PRO_PLAN_*           Pricing overrides, see pro/billing.py.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() in ("1", "true", "yes", "on")


def default_database_url() -> str:
    if os.environ.get("VERCEL"):
        return "sqlite:////tmp/homekeep-pro.db"           # the only writable folder on Vercel; not durable
    folder = ROOT / "instance"
    folder.mkdir(exist_ok=True)
    return f"sqlite:///{folder / 'homekeep-pro.db'}"


@dataclass
class ProConfig:
    database_url: str = field(default_factory=lambda: os.environ.get("PRO_DATABASE_URL") or default_database_url())
    secret_key: str = field(default_factory=lambda: os.environ.get("SECRET_KEY") or "")
    signup_enabled: bool = field(default_factory=lambda: _flag("PRO_SIGNUP", False))
    demo_enabled: bool = field(default_factory=lambda: _flag("PRO_DEMO", True))
    extractor: str = field(default_factory=lambda: os.environ.get("PRO_EXTRACTOR", "rules"))
    email_mode: str = field(default_factory=lambda: os.environ.get("PRO_EMAIL", "outbox"))
    # PRO_SITE=on makes this deployment the stand-alone HomeKeep Pro site: "/" opens /pro, and links to the free
    # checkup point at the public HomeKeep site instead of this one.
    pro_site: bool = field(default_factory=lambda: _flag("PRO_SITE", False))
    free_site_url: str = field(default_factory=lambda: os.environ.get("HOMEKEEP_FREE_URL", "https://www.myhomekeep.org/"))

    # Upload limits. Files are kept in the database for the pilot, so these also cap database growth. Vercel refuses
    # request bodies over 4.5 MB, so one file stays under 4 MB.
    max_upload_bytes: int = 4 * 1024 * 1024
    max_documents_per_case: int = 60
    max_firm_storage_bytes: int = 500 * 1024 * 1024
    max_pages_per_document: int = 60

    # Family links
    family_link_days: int = 14

    # Follow-up messages: the same template to the same person is blocked inside this window
    duplicate_message_hours: int = 24

    # Retention: closed cases are deleted this many days after closing unless the firm changes it
    default_retention_days: int = 365

    @property
    def secret_is_ephemeral(self) -> bool:
        return not self.secret_key

    def session_secret(self) -> str:
        if not self.secret_key:
            self.secret_key = secrets.token_hex(32)   # works for one instance; sign-ins reset when it restarts
        return self.secret_key
