"""Plans and limits for HomeKeep Pro. These prices are hypotheses to test in customer interviews, not settled terms.

No payment is taken by this code. When a business account exists, a payment processor will handle cards; HomeKeep
will never see or store card numbers. Every number can be overridden with an environment variable, for example
PRO_PLAN_PILOT_PRICE=750 or PRO_PLAN_MONTHLY_MATTERS=15.

Definitions used everywhere:
- A new matter is a case created during the plan period. Demo cases never count. Editing, reopening or adding
  documents to an existing case does not count again.
- Cases created earlier stay fully accessible after the period ends.
- Going over a limit never adds a charge. New cases are paused until the firm talks to us; nothing already stored is
  locked.
- The pilot does not renew. A monthly plan renews only after the firm says yes in writing, and can be cancelled any
  time; after cancelling, the firm can export or delete its data for 30 days.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    key: str
    label: str
    price_dollars: int
    period_days: int
    new_matters: int
    documents_per_matter: int
    storage_mb: int
    support_hours: int
    renews: bool


def _num(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def plans() -> dict[str, Plan]:
    return {
        "pilot": Plan("pilot", "30-day pilot", _num("PRO_PLAN_PILOT_PRICE", 500), 30,
                      _num("PRO_PLAN_PILOT_MATTERS", 10), 60, 500, _num("PRO_PLAN_PILOT_SUPPORT_HOURS", 4), False),
        "monthly": Plan("monthly", "Monthly (illustrative)", _num("PRO_PLAN_MONTHLY_PRICE", 399), 30,
                        _num("PRO_PLAN_MONTHLY_MATTERS", 10), 60, 500, _num("PRO_PLAN_MONTHLY_SUPPORT_HOURS", 2), True),
        "demo": Plan("demo", "Demo (fictional data)", 0, 3650, 1000, 60, 500, 0, False),
    }


def plan_for(key: str) -> Plan:
    return plans().get(key, plans()["pilot"])
