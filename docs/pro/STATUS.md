# HomeKeep Pro status

As of November 17, 2026, branch `homekeep-pro`. Nothing has been merged into `main`, and the live site at
www.myhomekeep.org is unchanged.

## Implemented (in code, on the branch)

- Firm workspace under `/pro`: sign-in, owner/attorney/staff roles, staff invitations, firm separation on every
  query, cases with assignment and status, checklist of outstanding items, activity history.
- Family intake: expiring, revocable links that show only the requested items; mobile-friendly upload and typed
  family details; no account needed.
- Documents: PDF/JPG/PNG only, signature and active-content checks, 4 MB per file, 60 per case, 500 MB per firm,
  family uploads quarantined until staff release them, access-controlled downloads, deletion with history,
  retention and automatic purge of closed cases.
- Reading: text extraction from ordinary PDFs; a rule-based extractor (no AI provider) behind a replaceable adapter;
  every suggested fact keeps its document, page and evidence line; family-reported, record and staff-confirmed
  values are kept apart; missing, unreadable, conflicting and awaiting-review states; instruction-like text in uploads
  is flagged and never acted on.
- Review: approve, correct or reject each fact with a reason and full history; conflict detection.
- Follow-ups: approved templates only, recorded consent, 24-hour duplicate block, outbox records (no sending).
- Packets: PDF and JSON with summary, inventory, approved facts with evidence, conflicts and missing items, marked
  for professional review; packet completion tracked apart from outcomes.
- Fictional demo firm with complete, incomplete and conflicting cases; an evaluation harness.
- Landing page with an honest description, pilot offer from configurable plans, working demo-request form with
  consent; a security page listing what is and isn't in place.
- Pilot measures panel in settings.
- Public site: corrected claims in English, Spanish and Somali, and a "For professionals" link in the footer.

## Drafted (needs founder review before use)

`PILOT_OFFER.md`, `SALES_KIT.md` (90-second demo, demo outline, first email, two follow-ups, phone intro, discovery
guide), `PRICING_AND_MODEL.md`, `financial_model.csv`, `GO_TO_MARKET.md` (tracker stages, weekly plan, measurement,
case studies, referrals), `DRAFT_TERMS.md` (pilot agreement and privacy notice outlines, for attorney review),
`BACKLOG.md`, `FOUNDER_CHECKLIST.md`, `SETUP.md`.

## Verified

- Vercel builds run the full test suite (`python -m pytest -q`) and fail on any failing test. These commits built
  successfully: `902c5fd` (Pro workspace), `d0f723d` (public claims), `118be73` (pilot measures, landing fixes, docs).
- Tests cover cross-firm access, tampered sessions, staff role limits, CSRF, sign-in throttling, family link scope,
  expired, revoked and closed-case links, quarantine downloads, malicious and oversize uploads, scans and broken
  files, prompt injection, conflicts, correction history, follow-up consent and duplicates, template placeholders,
  document and case deletion, plan limits without charges, packets, the demo, the evaluation harness, the financial
  model, pilot measures, and the removed public claims.
- The prospect list was checked against firms' own sites or named directories on November 17, 2026.
- Legal and fee facts in `CLAIMS_AUDIT.md` were checked against official pages on November 17, 2026 (some through
  search summaries, marked as such).

Not verified: the staging preview in a browser (it's behind Vercel's login), the exact number of tests that ran
(the Vercel log needs a signed-in browser), Spanish and Somali wording by native speakers, and anything about real
documents. Evaluation results so far come from fictional documents only and say nothing about real accuracy.

## Blocked

| What | Waiting on |
|---|---|
| Real firm data | Durable database, `SECRET_KEY`, malware scanning decision, attorney review of terms |
| Sending email | Email provider with a data processing agreement |
| Payments | Contracting party decision (some founders are under 18), processor account, reviewed agreement |
| OCR and AI reading | Provider choice, firm approval, cost limits, evaluation on permitted real samples |
| Outreach | Founders approving drafts and choosing a sender; nothing has been sent |
| Customer evidence | Interviews and pilots; none have happened |
