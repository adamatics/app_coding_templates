"""Chassis ORM models (spec §5).

The data model exists to make historical data **durable**:

* Results are append-only. A correction is a *new* row that supersedes the old one
  (``superseded_by`` points at the replacement). Nothing is mutated in place.
* "Resetting for a new class" means closing the open cohort and opening a new one —
  never deleting. Closed cohorts stay fully queryable and exportable.
* The only destructive operation is an admin hard-delete of a single bogus row
  (``deleted_at``), and it is audited.

DO NOT EDIT to change an exercise — the measurement shape lives in ``exercise/schema.py``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Cohort(Base):
    __tablename__ = "cohort"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")  # open | closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    groups: Mapped[list["Group"]] = relationship(back_populates="cohort")

    __table_args__ = (
        # At most one cohort may be 'open' at any time (spec §5). A partial unique
        # index gives us this guarantee at the database level, not just in code.
        Index(
            "uq_one_open_cohort",
            "status",
            unique=True,
            sqlite_where=text("status = 'open'"),
        ),
    )


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohort.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # Lower-cased key for case-insensitive uniqueness within a cohort (spec §5).
    name_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    cohort: Mapped["Cohort"] = relationship(back_populates="groups")
    members: Mapped[list["Member"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    results: Mapped[list["Result"]] = relationship(back_populates="group")

    __table_args__ = (
        UniqueConstraint("cohort_id", "name_key", name="uq_group_name_per_cohort"),
    )


class Member(Base):
    __tablename__ = "member"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    group: Mapped["Group"] = relationship(back_populates="members")


class Result(Base):
    __tablename__ = "result"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), nullable=False)
    # Validated against exercise.schema.Measurement at submit time; stored as JSON.
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    # When this row has been corrected, points at the replacement row (append-only).
    superseded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("result.id"), nullable=True
    )
    # Admin-only hard delete of a single bogus row (audited). Never set by students.
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    group: Mapped["Group"] = relationship(back_populates="results")

    __table_args__ = (
        Index("ix_result_group_id", "group_id"),
        Index("ix_result_superseded_by", "superseded_by"),
    )


class Audit(Base):
    """Append-only log of admin actions (login, cohort close, deletes, exports)."""

    __tablename__ = "audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    actor: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
