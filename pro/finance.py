"""A small, adjustable financial model for HomeKeep Pro. Every input is an assumption to replace with pilot data.

Founder time is costed at an hourly rate instead of treated as free. One-time pilot revenue is kept apart from monthly
subscription revenue, and contribution margin (revenue minus the costs that grow with each customer) is kept apart from
company profit (after fixed costs). A family's home value is never revenue, savings or impact attributable to HomeKeep.

Run `python -m pro.finance` to print the default scenario.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class Assumptions:
    customers: int = 5                      # paying firms on the monthly plan
    pilots_per_month: int = 2               # new 30-day pilots started each month
    monthly_price: float = 399.0
    pilot_price: float = 500.0
    matters_per_customer: float = 6.0       # new matters per firm per month (plan allows 10)
    documents_per_matter: float = 8.0
    pages_per_document: float = 3.0
    model_cost_per_page: float = 0.0        # 0 while extraction is rule-based; set from provider pricing if AI is used
    ocr_cost_per_page: float = 0.0          # 0 until OCR is set up
    storage_cost_per_customer: float = 2.0  # database and file storage, per firm per month
    messages_per_matter: float = 4.0
    cost_per_message: float = 0.001         # email delivery
    payment_fee_rate: float = 0.029         # card processing percentage
    payment_fee_fixed: float = 0.30         # card processing per charge
    support_hours_per_customer: float = 2.0     # per month, after onboarding
    onboarding_hours_per_new_customer: float = 6.0
    founder_hourly_rate: float = 35.0       # what founder time is worth; not zero
    hosting_fixed: float = 20.0             # per month
    professional_review_fixed: float = 250.0    # legal/security review, spread per month
    insurance_fixed: float = 100.0          # per month, if a policy is bought
    acquisition_hours_per_customer: float = 15.0    # outreach, calls and demos per paying customer won
    acquisition_cash_per_customer: float = 0.0      # no paid advertising planned


def monthly(a: Assumptions) -> dict:
    matters = a.customers * a.matters_per_customer
    pages = matters * a.documents_per_matter * a.pages_per_document
    variable_per_customer = (
        a.matters_per_customer * a.documents_per_matter * a.pages_per_document * (a.model_cost_per_page + a.ocr_cost_per_page)
        + a.storage_cost_per_customer
        + a.matters_per_customer * a.messages_per_matter * a.cost_per_message
        + a.monthly_price * a.payment_fee_rate + a.payment_fee_fixed
        + a.support_hours_per_customer * a.founder_hourly_rate)
    contribution_per_customer = a.monthly_price - variable_per_customer
    subscription_revenue = a.customers * a.monthly_price
    pilot_revenue = a.pilots_per_month * a.pilot_price
    pilot_costs = a.pilots_per_month * (a.onboarding_hours_per_new_customer * a.founder_hourly_rate
                                        + a.pilot_price * a.payment_fee_rate + a.payment_fee_fixed)
    fixed = a.hosting_fixed + a.professional_review_fixed + a.insurance_fixed
    contribution = a.customers * contribution_per_customer + (pilot_revenue - pilot_costs)
    acquisition_cost = a.acquisition_hours_per_customer * a.founder_hourly_rate + a.acquisition_cash_per_customer
    return {
        "matters": matters, "pages": pages,
        "subscription_revenue": round(subscription_revenue, 2), "pilot_revenue_one_time": round(pilot_revenue, 2),
        "variable_cost_per_customer": round(variable_per_customer, 2),
        "contribution_per_customer": round(contribution_per_customer, 2),
        "contribution_margin_pct": round(100 * contribution_per_customer / a.monthly_price, 1) if a.monthly_price else 0,
        "fixed_costs": round(fixed, 2),
        "company_profit": round(contribution - fixed, 2),
        "break_even_customers": (math.ceil(fixed / contribution_per_customer) if contribution_per_customer > 0
                                 else None),
        "acquisition_cost_per_customer": round(acquisition_cost, 2),
        "payback_months": (round(acquisition_cost / contribution_per_customer, 1) if contribution_per_customer > 0
                           else None),
    }


def sensitivity(a: Assumptions, field: str, values: list[float]) -> list[tuple[float, dict]]:
    return [(v, monthly(replace(a, **{field: v}))) for v in values]


if __name__ == "__main__":
    base = Assumptions()
    for key, value in asdict(base).items():
        print(f"  {key}: {value}")
    print()
    for key, value in monthly(base).items():
        print(f"{key}: {value}")
    print("\nSupport hours per customer per month:")
    for hours, result in sensitivity(base, "support_hours_per_customer", [1, 2, 4, 6, 8]):
        print(f"  {hours}: contribution/customer {result['contribution_per_customer']}, "
              f"break-even {result['break_even_customers']}")
