# HomeKeep Pro: implementation plan

Branch: `homekeep-pro`. Staging: the Vercel preview URL for that branch. Production (`www.myhomekeep.org`, branch `main`)
is not touched until the founders approve a merge.

## What exists today (audited November 2026)

The free site is a stateless Flask app on Vercel. It has no accounts, no database, no application logging and no
analytics. Every page and question works in English, Spanish and Somali; the Spanish and Somali were written by an AI
model and have not been reviewed by native speakers.

Working features, all verified on the live site in October 2026: Franklin County address lookup through the Auditor's
public ArcGIS service, the lot and neighbor map, the title questions and five-status result, the step-by-step plan with
time, cost and office per step, both PDFs, the homestead savings estimate by tax district, the inheritance and equity
calculator, the free-help office map, the editable About and Learn pages, and the larger-text switch. The demo home and
its block are invented.

What a visitor's browser and our server send to other services:

| Recipient | What it receives | When |
|---|---|---|
| Franklin County Auditor ArcGIS (`gis.franklincountyohio.gov`) | The typed street address, cleaned to letters, numbers and spaces | Every lookup (sent by our server) |
| Google Fonts | Visitor IP address and browser details | Every page |
| jsDelivr, cdnjs, code.jquery.com, bootstrapcdn | Visitor IP address | Every page with a map |
| OpenStreetMap and Esri tile servers | Visitor IP and the map area being viewed | Every map |
| Vercel | Request logs: page path, query string, IP, browser | Every request |

HomeKeep itself stores nothing a visitor types, but "Nothing you type is saved" is broader than the facts above. The
public privacy wording changes as part of this work.

The legal and financial wording also needs care before firms see it (see `CLAIMS_AUDIT.md`): a few lines read as
universal rules (every heir must sign, a tangled title blocks disaster aid, one $34 form is the fix), and the
inheritance calculator calls a home's market value "family wealth," which is not the same as equity.

## The smallest credible pilot

Positioning to test: "Get inherited-home cases ready for attorney review with less document chasing."

First customer to test: a small Ohio firm handling probate matters with a residential home, Franklin County first. The
buyer is a managing or probate attorney or the office manager; the daily user is a paralegal or intake coordinator.

Pilot hypothesis: $500 for 30 days, up to 10 new matters, with document and support limits. Price and limits live in
configuration because interviews may show they are wrong. The deliverable is an organized, staff-reviewed intake
packet and a missing-information workflow. It is not legal advice, title clearance, estate resolution or a promise
that a filing will be accepted.

## What gets built, in order

1. Firm accounts and roles. Email and password sign-in, three roles (owner, attorney, staff), staff invitations by
   link, and every database query scoped to one firm.
2. Cases. Create, assign, status, a checklist of outstanding items from a firm template, and an activity history that
   records every consequential change with who made it.
3. Family intake. A staff member invites a relative with an expiring link that opens one simple phone page showing only
   the requests made of that person. No dashboard and no account.
4. Documents. Upload validation by file signature as well as extension, size and count limits, a quarantine state until
   staff release a file, downloads only through access checks, retention settings and a deletion workflow. Files are
   stored in the database for the pilot so firm separation is enforced in one place. There is no malware scanner on
   this hosting; quarantine plus forced-download headers is the interim control.
5. Extraction. Plain text from text-based PDFs, then a field extractor behind a replaceable adapter. The default
   extractor is rule-based and works offline, which is also the mock mode for demos and tests. No AI provider is
   connected: whether one adds measurable value is still a hypothesis, and choosing one needs the evaluation below plus
   a review of its data-use terms. Every field keeps its source document, page and quoted evidence, and a source type:
   reported by family, appears in a record, or confirmed by staff. States are missing, unreadable, conflicting,
   awaiting review and approved. Document text is treated as data; nothing in a document can trigger an action.
6. Review screen. Each extracted field beside its evidence, with approve and correct. Corrections keep history.
7. Follow-ups. Staff-approved email templates, recorded consent and preferences, a delivery log, and a block on
   duplicate sends. Nothing is sent without a staff click. Email delivery is a mock outbox until an email provider is
   authorized. No SMS.
8. Case packet. A PDF and a JSON export with the summary, document inventory, approved fields, unresolved conflicts,
   missing items and evidence references, marked "Prepared for professional review."
9. Billing preparation. Plan definitions and usage counting in configuration, test mode only. No card data ever
   touches HomeKeep; a payment processor will handle it once a business account exists.
10. Synthetic demo. A fictional firm with three fictional families: a straightforward case, a case missing documents,
    and a case with conflicting information. Fictional PDFs are generated by the app itself.
11. A professional landing page with a demo-request form, linked from the free site as "For professionals."

The free checkup, education pages, accessibility features and free-help referrals stay as they are and stay free. The
professional section never receives information from the public site.

## Hosting limits that block a real pilot

| Need | Today | Blocked on |
|---|---|---|
| Durable database | SQLite in the function's temporary folder (resets on cold start) | Founders authorizing a hosted Postgres database |
| Stable sign-in sessions | Random key per instance unless `SECRET_KEY` is set | Setting `SECRET_KEY` in the Vercel project |
| Email delivery | Mock outbox | Choosing and authorizing an email provider |
| Payments | Plan configuration only | A business payment account, legal review (some founders are minors) |
| Malware scanning | Quarantine only | A scanning service the founders approve |
| AI extraction | Rule-based mock | Evaluation on authorized, de-identified examples and a provider terms review |

## How results will be checked

The automated tests run on every Vercel build. New tests cover cross-firm access, family-link permissions and expiry,
malicious and oversized uploads, deletion, duplicate reminders, extraction failure, and instructions embedded in
documents. The evaluation harness scores extraction against labeled examples: field errors, unsupported values,
missing evidence references, and processing time. Scores on the synthetic documents only show that the plumbing works;
they say nothing about accuracy on real deeds or death certificates.
