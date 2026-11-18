# Backlog

Ordered by what blocks a real pilot first. "Blocked" means it needs a founder decision, an account or money.

## Before any real firm data (blocked on founders)

1. Durable Postgres database with backups and encryption at rest; set `PRO_DATABASE_URL` for Preview, then Production.
2. `SECRET_KEY` in Vercel for Preview and Production.
3. Attorney review of `DRAFT_TERMS.md`, the security page and the public claims; decide the contracting party.
4. Decide on malware scanning for uploads (a scanning service, or keep files quarantined until staff open them on a
   protected machine). Today family uploads stay quarantined until staff release them, and nothing is scanned.
5. File storage plan: files live in the database today, capped at 4 MB each and 500 MB per firm.

## Product, next

6. Test the rule-based reader on real, redacted or sample Ohio deeds and death certificates (with permission); expect
   it to miss most fields because real documents aren't "Label: value" text.
7. Done (free): OCR for scans and phone photos runs in the staff member's browser with self-hosted Tesseract.js and pdf.js. Next: test it on permitted real documents; consider server-side OCR only if browser OCR is too slow.
8. Optional AI extraction behind the same adapter, off by default, with a spending cap, usage logging, the existing
   prompt-injection checks, and the firm's written approval of the provider. Compare against the rules reader with
   `pro/evaluate.py` before turning it on.
9. Email sending through a provider with a data processing agreement; keep the approved-template, consent and
   duplicate rules. Delivery and bounce tracking.
10. Spanish and Somali family pages, reviewed by native speakers before they're used, and labeled as such.
11. Two-factor sign-in for staff; password reset by email.
12. Done: staff time notes per case, counted in Pilot measures.
13. Per-firm checklist editing (today every firm starts from the same template and can mark items not needed).

## Later

14. Clio or other practice-software export (CSV first, no integration until a firm asks).
15. More counties' public records, each with its own terms checked first.
16. Done: whole-firm JSON export (document files still download per case because of the 4.5 MB response limit).

## Known gaps in what's built

- Vercel preview SQLite resets on cold start; demo data reseeds itself.
- No rate limit on family uploads beyond file count and size limits.
- No audit export; activity history is visible per case only.
