# Setting up HomeKeep Pro

HomeKeep Pro lives in the same Flask app as the free homeowner checkup. The free pages are at `/`, and the firm
workspace is under `/pro`. Nothing here needs a new service to try it: by default it uses SQLite and records
follow-up emails instead of sending them.

## Run it on your own computer

You need Python 3.12.

```bash
python -m venv .venv
```

```bash
.venv/Scripts/pip install -r requirements.txt
```

```bash
.venv/Scripts/python -m pytest -q
```

```bash
.venv/Scripts/flask --app app run --debug
```

Open http://127.0.0.1:5000/pro and click **Try the demo**. The demo signs you in to a fictional firm with three
fictional cases. On macOS or Linux, use `.venv/bin/` instead of `.venv/Scripts/`.

The local database is `instance/homekeep-pro.db`. It's ignored by git. Delete it to start over.

## Environment variables

Names only. Never put values in the repo, in docs, in commit messages or in chat.

| Name | What it does | Default if unset |
|---|---|---|
| `SECRET_KEY` | Signs session cookies. Use a long random value per environment. | A random key per process, so sign-ins reset on every cold start. A banner says so. |
| `PRO_DATABASE_URL` | SQLAlchemy URL for the Pro database, for example a Postgres URL. | SQLite in `/tmp` on Vercel (wiped on cold start), or `instance/homekeep-pro.db` locally. |
| `PRO_DEMO` | `on` seeds the fictional demo firm and shows the demo button. | on |
| `PRO_SIGNUP` | `on` lets anyone create a firm account at `/pro/signup`. Keep it off until there are terms and a durable database. | off |
| `PRO_SITE` | `on` makes the deployment the stand-alone HomeKeep Pro site: `/` opens `/pro`, and "Free homeowner checkup" links go to `HOMEKEEP_FREE_URL`. Set it only in the separate `homekeep-pro` Vercel project. | off |
| `HOMEKEEP_FREE_URL` | Where the stand-alone Pro site sends people looking for the free checkup. | https://www.myhomekeep.org/ |
| `PRO_EXTRACTOR` | Which extractor reads PDFs. Only `rules` exists. | rules |
| `PRO_EMAIL` | `outbox` records messages without sending. There is no sending mode yet. | outbox |
| `PRO_PLAN_PILOT_PRICE`, `PRO_PLAN_PILOT_MATTERS`, `PRO_PLAN_PILOT_SUPPORT_HOURS` | Pilot plan numbers shown on the landing page and enforced as limits. | 500, 10, 4 |
| `PRO_PLAN_MONTHLY_PRICE`, `PRO_PLAN_MONTHLY_MATTERS`, `PRO_PLAN_MONTHLY_SUPPORT_HOURS` | Monthly plan numbers. | 399, 10, 2 |

## The separate HomeKeep Pro project

HomeKeep Pro has its own Vercel project, `homekeep-pro`, at https://homekeep-pro.vercel.app (set up November 17,
2026). It deploys the `homekeep-pro` branch as its production, has `PRO_SITE=on` and its own `SECRET_KEY`, and its
Ignored Build Step is "Only build production," so it builds nothing else. The original project
(`hometitlecheckup-h5fn`, www.myhomekeep.org) has a custom Ignored Build Step that skips the `homekeep-pro` branch.
`tests/conftest.py` clears the site settings so the tests behave the same in both projects.

Database: a free Neon Postgres database (Vercel Marketplace, Free plan, region Cleveland `cle1`, Neon Auth off) is
connected to the `homekeep-pro` project only, for Production and Preview, since November 18, 2026. Vercel provides
`DATABASE_URL` (and other `POSTGRES_*` / `PG*` variables); the app reads `DATABASE_URL`. Free plan limits: 1 GB storage
and 100 compute-hours a month. The data, including the public demo firm, now persists between deploys. Real client
data still waits on attorney review of the terms and a malware-scanning decision.

## Staging on Vercel

Every push to a branch other than `main` gets a Vercel preview URL. The `homekeep-pro` branch preview is the staging
site. Vercel runs `python -m pytest -q` as the build command, so a failing test stops the deploy.

Preview URLs are behind Vercel's login (Deployment Protection). Team members sign in to Vercel to see them. Don't turn
protection off for a preview that holds anything but fictional data.

To make staging closer to real use:

1. In Vercel, open the project, then **Settings > Environment Variables**.
2. Add `SECRET_KEY` for the **Preview** environment only. Generate the value on your own computer, for example with
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`, and paste it straight into Vercel.
3. When a durable database exists (see below), add `PRO_DATABASE_URL` for **Preview** only.
4. Redeploy the branch.

## Before any real firm data

These are blockers, not suggestions. `docs/pro/PLAN.md` explains each.

1. A durable Postgres database with encryption at rest and backups, in a region you have written down. Vercel
   Marketplace offers Postgres providers; pick one, read its data processing terms, and list it in the security page.
2. `SECRET_KEY` set in Production.
3. File storage that isn't the database, or a documented size plan for keeping files in Postgres.
4. Malware scanning for uploads, or a written decision to keep files quarantined until staff open them on a
   protected machine.
5. An email provider with a signed data processing agreement, if follow-ups will actually send.
6. An attorney's review of the pilot agreement, privacy notice and security page (some founders are under 18, which
   affects who can sign contracts).
7. A decision on whether any AI provider will ever see firm documents. Today none does.

## Production

Production is `main`, served at www.myhomekeep.org. Merging `homekeep-pro` into `main` puts `/pro` on the live site.
Don't merge until the founders decide to, in writing, and the blockers above are handled or the Pro pages are
switched off. Nothing in this branch has been merged or deployed to production.
