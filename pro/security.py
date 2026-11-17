"""Passwords, link tokens, roles and form protection for HomeKeep Pro.

Link tokens (staff invitations, family links) are random and only their SHA-256 hash is stored, so a copy of the
database cannot be turned into working links.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

from werkzeug.security import check_password_hash, generate_password_hash

ROLES = ("owner", "attorney", "staff")
ROLE_NAMES = {"owner": "Owner", "attorney": "Attorney", "staff": "Staff"}

# What each role may do. Attorneys approve; owners also manage staff, settings and billing.
PERMISSIONS = {
    "owner": {"cases", "review", "approve", "send", "staff", "settings", "delete"},
    "attorney": {"cases", "review", "approve", "send", "delete"},
    "staff": {"cases", "review", "send"},
}

MIN_PASSWORD = 10


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def check_password(hashed: str, password: str) -> bool:
    return check_password_hash(hashed, password)


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    return None


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def can(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def csrf_token(session) -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]


def csrf_ok(session, sent: str | None) -> bool:
    expected = session.get("csrf")
    return bool(expected and sent and hmac.compare_digest(expected, sent))


class Throttle:
    """At most `limit` attempts per key per `window` seconds, per server instance. Slows password guessing."""

    def __init__(self, limit: int = 8, window: int = 600):
        self.limit, self.window = limit, window
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        stamp = time.monotonic()
        hits = self.hits[key]
        while hits and stamp - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(stamp)
        return True
