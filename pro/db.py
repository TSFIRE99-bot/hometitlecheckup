"""Database tables for HomeKeep Pro (SQLAlchemy Core, so the same code runs on SQLite now and Postgres later).

Every table except demo_requests carries firm_id, and every query in pro/store.py filters on it. Documents are stored
in the database for the pilot so firm separation is enforced in one place, not split between a database and a bucket.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, MetaData, String, Table, Text,
                        create_engine)
from sqlalchemy.engine import Engine

metadata = MetaData()


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)     # stored as naive UTC on every database


def _id():
    return Column("id", Integer, primary_key=True)


def _firm():
    return Column("firm_id", Integer, ForeignKey("firms.id"), nullable=False, index=True)


firms = Table("firms", metadata, _id(),
              Column("name", String(200), nullable=False),
              Column("plan", String(40), nullable=False, default="pilot"),
              Column("plan_started_at", DateTime, nullable=False, default=now),
              Column("retention_days", Integer, nullable=False, default=365),
              Column("checklist_approved_by", Integer),        # user id of the attorney who approved the template
              Column("checklist_approved_at", DateTime),
              Column("is_demo", Boolean, nullable=False, default=False),
              Column("created_at", DateTime, nullable=False, default=now))

users = Table("users", metadata, _id(), _firm(),
              Column("email", String(254), nullable=False, unique=True),
              Column("name", String(200), nullable=False),
              Column("password_hash", String(300), nullable=False),
              Column("role", String(20), nullable=False),      # owner, attorney, staff
              Column("active", Boolean, nullable=False, default=True),
              Column("created_at", DateTime, nullable=False, default=now))

invites = Table("invites", metadata, _id(), _firm(),
                Column("email", String(254), nullable=False),
                Column("role", String(20), nullable=False),
                Column("token_hash", String(64), nullable=False, unique=True),
                Column("expires_at", DateTime, nullable=False),
                Column("used_at", DateTime),
                Column("created_by", Integer, nullable=False))

cases = Table("cases", metadata, _id(), _firm(),
              Column("reference", String(80), nullable=False),          # the firm's own matter number
              Column("title", String(200), nullable=False),
              Column("decedent_name", String(200)),
              Column("property_address", String(300)),
              Column("parcel_id", String(40)),
              Column("county", String(60), nullable=False, default="Franklin"),
              Column("status", String(30), nullable=False, default="intake"),
              Column("assigned_to", Integer),
              Column("created_by", Integer),
              Column("created_at", DateTime, nullable=False, default=now),
              Column("packet_ready_at", DateTime),        # tracked apart from any legal outcome
              Column("closed_at", DateTime),
              Column("delete_after", DateTime),
              Column("record_source", Text),             # public-record URL, retrieval date and limits, as JSON text
              Column("counts_toward_plan", Boolean, nullable=False, default=True))

items = Table("items", metadata, _id(), _firm(),
              Column("case_id", Integer, ForeignKey("cases.id"), nullable=False, index=True),
              Column("key", String(60), nullable=False),
              Column("label", String(200), nullable=False),
              Column("kind", String(20), nullable=False),        # document or information
              Column("required", Boolean, nullable=False, default=True),
              Column("status", String(20), nullable=False, default="missing"),   # missing, requested, received,
              Column("note", Text),                                            # approved, not_needed
              Column("updated_at", DateTime, nullable=False, default=now))

participants = Table("participants", metadata, _id(), _firm(),
                     Column("case_id", Integer, ForeignKey("cases.id"), nullable=False, index=True),
                     Column("name", String(200), nullable=False),
                     Column("email", String(254)),
                     Column("relation", String(80)),
                     Column("token_hash", String(64), unique=True),
                     Column("expires_at", DateTime),
                     Column("revoked", Boolean, nullable=False, default=False),
                     Column("email_consent", Boolean, nullable=False, default=False),
                     Column("consent_recorded_at", DateTime),
                     Column("consent_recorded_by", Integer),
                     Column("created_at", DateTime, nullable=False, default=now))

participant_items = Table("participant_items", metadata, _id(), _firm(),
                          Column("participant_id", Integer, ForeignKey("participants.id"), nullable=False, index=True),
                          Column("item_id", Integer, ForeignKey("items.id"), nullable=False))

documents = Table("documents", metadata, _id(), _firm(),
                  Column("case_id", Integer, ForeignKey("cases.id"), nullable=False, index=True),
                  Column("item_id", Integer),
                  Column("participant_id", Integer),
                  Column("uploaded_by", Integer),
                  Column("filename", String(255), nullable=False),
                  Column("content_type", String(80), nullable=False),
                  Column("size", Integer, nullable=False),
                  Column("sha256", String(64), nullable=False),
                  Column("data", LargeBinary),                     # set to NULL when the document is deleted
                  Column("status", String(20), nullable=False, default="quarantined"),   # released, deleted
                  Column("doc_type", String(40)),
                  Column("doc_type_evidence", Text),
                  Column("text_status", String(20)),               # ok, no_text, not_pdf, too_long, error
                  Column("page_count", Integer),
                  Column("created_at", DateTime, nullable=False, default=now),
                  Column("deleted_at", DateTime))

pages = Table("pages", metadata, _id(), _firm(),
              Column("document_id", Integer, ForeignKey("documents.id"), nullable=False, index=True),
              Column("page", Integer, nullable=False),
              Column("text", Text, nullable=False))

fields = Table("fields", metadata, _id(), _firm(),
               Column("case_id", Integer, ForeignKey("cases.id"), nullable=False, index=True),
               Column("key", String(60), nullable=False),
               Column("value", Text),
               Column("source", String(20), nullable=False),        # family, record, staff
               Column("document_id", Integer),
               Column("page", Integer),
               Column("evidence", Text),                            # the quoted text the value came from
               Column("reported_by", Integer),                      # participant id when source is family
               Column("state", String(20), nullable=False, default="awaiting_review"),
               Column("reviewed_by", Integer),
               Column("reviewed_at", DateTime),
               Column("created_at", DateTime, nullable=False, default=now))

field_history = Table("field_history", metadata, _id(), _firm(),
                      Column("field_id", Integer, ForeignKey("fields.id"), nullable=False),
                      Column("old_value", Text),
                      Column("new_value", Text),
                      Column("old_state", String(20)),
                      Column("new_state", String(20)),
                      Column("changed_by", Integer, nullable=False),
                      Column("reason", Text),
                      Column("changed_at", DateTime, nullable=False, default=now))

activity = Table("activity", metadata, _id(), _firm(),
                 Column("case_id", Integer, index=True),
                 Column("actor", String(60), nullable=False),        # user:3, participant:7 or system
                 Column("action", String(60), nullable=False),
                 Column("detail", Text),
                 Column("created_at", DateTime, nullable=False, default=now))

templates = Table("templates", metadata, _id(), _firm(),
                  Column("name", String(120), nullable=False),
                  Column("subject", String(200), nullable=False),
                  Column("body", Text, nullable=False),
                  Column("approved_by", Integer),
                  Column("approved_at", DateTime))

outbox = Table("outbox", metadata, _id(), _firm(),
               Column("case_id", Integer, nullable=False),
               Column("participant_id", Integer, nullable=False),
               Column("template_id", Integer, nullable=False),
               Column("to_email", String(254), nullable=False),
               Column("subject", String(200), nullable=False),
               Column("body", Text, nullable=False),
               Column("status", String(20), nullable=False),          # recorded, sent, failed
               Column("created_by", Integer, nullable=False),
               Column("created_at", DateTime, nullable=False, default=now))

time_entries = Table("time_entries", metadata, _id(), _firm(),         # staff minutes, typed in by staff themselves
                     Column("case_id", Integer, nullable=False, index=True),
                     Column("user_id", Integer, nullable=False),
                     Column("minutes", Integer, nullable=False),
                     Column("kind", String(20), nullable=False),       # chasing, review, other
                     Column("note", String(200)),
                     Column("created_at", DateTime, nullable=False, default=now))

usage = Table("usage", metadata, _id(), _firm(),
              Column("case_id", Integer),
              Column("kind", String(40), nullable=False),     # pages_read, model_calls, model_cost_cents, ...
              Column("amount", Integer, nullable=False),
              Column("created_at", DateTime, nullable=False, default=now))

demo_requests = Table("demo_requests", metadata, _id(),
                      Column("name", String(200), nullable=False),
                      Column("firm", String(200), nullable=False),
                      Column("email", String(254), nullable=False),
                      Column("role", String(120)),
                      Column("message", Text),
                      Column("consent", Boolean, nullable=False),
                      Column("created_at", DateTime, nullable=False, default=now))


def make_engine(url: str) -> Engine:
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
    engine = create_engine(url, future=True, **kwargs)
    metadata.create_all(engine)
    return engine
