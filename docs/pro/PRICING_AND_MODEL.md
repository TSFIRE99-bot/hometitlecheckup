# Pricing assumptions and financial model

Everything here is a hypothesis. No firm has been interviewed, no firm has agreed to a price, and no money has been
collected. Willingness to pay, time savings and profitability are what the pilots are meant to test.

## Pricing hypotheses

| Hypothesis | Starting guess | How we'll test it | What would change our mind |
|---|---|---|---|
| A small firm will pay for a short pilot | $500 for 30 days, up to 10 new matters | Ask in discovery calls what the problem costs them; offer the pilot to firms that describe real pain | Three firms in a row say the problem is real but won't pay anything to try it |
| Some will continue monthly | $399/month, 10 new matters (illustrative) | Ask at the end of each pilot, after showing them their own measures | Pilot firms don't use it in week 3 and 4, or say it saves under an hour a month |
| Pricing per new matter fits how firms think | "New matter" = a case created in the period | Ask how they bill estates and how they'd want to be billed | Firms prefer flat fees per attorney, or per-estate pricing |
| No overage charges | New cases pause at the limit | Watch whether anyone hits the limit | Firms routinely need 20+ matters, so the tiers are wrong |

Billing rules, already in `pro/billing.py`: a new matter is a case created in the plan period (demo cases never
count); going over a limit never adds a charge; the pilot doesn't renew; a monthly plan renews only with written
consent and can be cancelled any time; after cancelling, the firm has 30 days to export or delete. All prices can be
changed with environment variables. Payment isn't connected. When it is, a payment processor's test mode comes
first, HomeKeep never sees card numbers, and an adult (not a founder under 18) signs the processor agreement.

## Financial model

Two copies with the same defaults:

- `docs/pro/financial_model.csv`: open in Excel or Google Sheets, change column B, and the results recalculate.
- `pro/finance.py`: the same math in code, tested in `tests/test_pro.py`.

Rules the model follows: founder time is a cost ($35 an hour by default); one-time pilot revenue is kept apart from
recurring revenue; contribution (price minus costs that grow with each firm) is kept apart from company profit
(after fixed costs, including founder product time); and a family's home value is never counted as revenue, savings
or impact.

### Default scenario (5 paying firms, 2 pilots a month, 1 new paying firm a month)

| Result | Value |
|---|---|
| Variable cost per firm per month | $83.90 (mostly 2 support hours at $35) |
| Contribution per firm per month | $315.11 (79% of the price) |
| Subscription revenue | $1,995 a month |
| Pilot revenue | $1,000 this month, one time |
| Pilot contribution | $550.40, one time (6 onboarding hours per pilot at $35) |
| Fixed costs | $1,070 a month ($370 cash plus 20 founder product hours) |
| Company profit before acquisition time | $1,055.93 |
| Profit without pilot revenue | $505.53 |
| Acquisition cost per firm won | $525 (15 founder hours) |
| Profit after acquisition time | $530.93 |
| Break-even | 4 paying firms (recurring only) |
| Payback on acquisition | 1.7 months |

What this says, candidly: at 5 paying firms and 1 new firm a month, recurring revenue alone ($505.53) doesn't cover
the founders' time spent winning the next firm ($525). The business only works on paper if support stays near 2
hours per firm, firms keep paying after the pilot, and winning a firm takes about 15 hours. All three are unknown.

### Sensitivity

Support hours per firm per month (everything else at defaults):

| Support hours | Contribution per firm | Break-even firms |
|---|---|---|
| 1 | $350.11 | 4 |
| 2 | $315.11 | 4 |
| 4 | $245.11 | 5 |
| 6 | $175.11 | 7 |
| 8 | $105.11 | 11 |

Monthly price (everything else at defaults):

| Price | Contribution per firm | Break-even firms |
|---|---|---|
| $199 | $120.91 | 9 |
| $250 | $170.43 | 7 |
| $399 | $315.11 | 4 |
| $599 | $509.31 | 3 |

AI costs are $0 because nothing calls an AI model. If one is added later, set the AI cost per page from the
provider's published pricing; at the default 144 pages per firm a month, even a few cents a page is small next to
support time.

## Assumptions to validate first

1. How many inherited-home matters a small firm opens a month (we assume 6).
2. Staff minutes spent chasing documents per matter today (unknown; this is the baseline).
3. Support hours a pilot firm needs (we assume 6 to onboard, then 2 a month).
4. Hours to win one paying firm (we assume 15).
5. Whether firms will let families upload to a student-built tool at all, and what they need to see first.
