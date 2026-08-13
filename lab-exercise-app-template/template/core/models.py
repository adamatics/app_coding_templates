"""Chassis ORM models (CHASSIS, framework-free — no streamlit).

Identity levels (Addendum B §B2): Individual (KUID) -> Group (carries hold) -> Hold ->
Year (a cohort). Every result links to the individual and the group, so any view can filter
at any level. Durability rules from the base spec are unchanged: append-only results with
supersede, close-cohort-never-delete, admin-only single-row hard delete.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Bump ONLY when an existing table changes shape. A brand-new table needs no bump —
# ``create_all`` adds those on the next start. But it never ALTERs an existing table, so a
# column added here would silently be missing on a deployed app and blow up later with a
# confusing SQL error. Startup compares this against the value stored in the database and
# refuses to run on a mismatch (see core/db.py), which is the same fail-loud stance as storage.
SCHEMA_VERSION = 2


class Base(DeclarativeBase):
    pass


class Cohort(Base):
    """A Year (§B2). Exactly one is open at a time; 'reset for a new class' closes it and
    opens the next — never deletes."""

    __tablename__ = "cohort"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String, unique=True, nullable=False)  # e.g. "2026"
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")  # open | closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    groups: Mapped[list["Group"]] = relationship(back_populates="cohort")

    __table_args__ = (
        Index("uq_one_open_cohort", "status", unique=True, sqlite_where=text("status = 'open'")),
    )


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohort.id"), nullable=False)
    hold: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1..7 (§B2)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_key: Mapped[str] = mapped_column(String, nullable=False)  # lower(name), uniqueness
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    cohort: Mapped["Cohort"] = relationship(back_populates="groups")
    members: Mapped[list["Member"]] = relationship(back_populates="group")

    __table_args__ = (
        UniqueConstraint("cohort_id", "name_key", name="uq_group_name_per_cohort"),
    )


class Member(Base):
    """An individual, identified by KUID (3 letters + 3 digits, §B2). No per-student password."""

    __tablename__ = "member"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), nullable=False)
    # Denormalised from the group so the database itself can guarantee one registration per
    # KUID per year. Without it, "look up then insert" in register() is a check-then-act race:
    # two tabs could split one student across two member rows, and their results with them.
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohort.id"), nullable=False)
    kuid: Mapped[str] = mapped_column(String, nullable=False)
    kuid_key: Mapped[str] = mapped_column(String, nullable=False)  # lower(kuid)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    group: Mapped["Group"] = relationship(back_populates="members")

    __table_args__ = (
        Index("ix_member_kuid_key", "kuid_key"),
        UniqueConstraint("cohort_id", "kuid_key", name="uq_member_kuid_per_cohort"),
    )


class Result(Base):
    __tablename__ = "result"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("member.id"), nullable=False)
    # Snapshot of the group the measurement was made in (immutable provenance).
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    superseded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("result.id"), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_result_member_id", "member_id"),
        Index("ix_result_group_id", "group_id"),
        Index("ix_result_superseded_by", "superseded_by"),
    )


class Answer(Base):
    """Free-text answers to the teacher's analysis questions, stored per group (§B3, §B5)."""

    __tablename__ = "answer"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("group_id", "question_id", name="uq_answer_group_question"),
    )


class Setting(Base):
    """Key-value course metadata (§B6): course name, instructor, links, documents, active
    message banner, permitted retrieval scope, FAQ content, active identity layers."""

    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Document(Base):
    """A file the teacher uploads for students to download (øvelsesvejledning, data sheets…).

    The bytes live on the shared volume next to the database; this row is the metadata. A new
    table needs no SCHEMA_VERSION bump — ``create_all`` adds it on the next start.
    """

    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)        # as stored on disk
    original_name: Mapped[str] = mapped_column(String, nullable=False)   # as the teacher named it
    label: Mapped[str] = mapped_column(String, nullable=False, default="")
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    content_type: Mapped[str] = mapped_column(String, nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (Index("ix_document_sort_order", "sort_order"),)


class SessionToken(Base):
    """A browser session that survives a refresh, WITHOUT per-student passwords (§B2).

    The student's browser holds an opaque random token in the URL; this row is the only place
    it maps to a person. Only the SHA-256 hash is stored, so a database copy yields no usable
    tokens, and no personal data (KUID/name) ever appears in a URL, browser history or proxy
    log. ``member_id`` is null for a token issued at the course gate before registration.
    """

    __tablename__ = "session_token"

    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("member.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (Index("ix_session_token_expires_at", "expires_at"),)


class Event(Base):
    """Append-only event log covering every actor, not just admins.

    Generalises the base spec's ``audit`` table (§5): admin actions are still recorded, and so
    are student registrations, submissions, corrections (overwrites), exports and errors. One
    log means one place to answer "what happened in that lab session?".

    Rows are never updated or deleted by the app — only pruned by an explicit admin action.
    """

    __tablename__ = "event"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False, default="info")  # info|warning|error
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False, default="system")  # kuid|admin|system
    # Identity context, denormalised so the log stays readable after groups are merged/renamed.
    member_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kuid: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    group_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    group_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_event_created_at", "created_at"),
        Index("ix_event_action", "action"),
        Index("ix_event_level", "level"),
        Index("ix_event_kuid", "kuid"),
    )
