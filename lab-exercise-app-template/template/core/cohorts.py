"""Cohort (Year) lifecycle: close-never-delete (CHASSIS, no streamlit).

'Reset for a new class' closes the open year and opens the next. Closed years stay fully
queryable and exportable forever — no code path drops historical data (base spec §5).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import events
from .errors import ConflictError, NotFoundError, ValidationError
from .models import Cohort, Group, Member, Result


def get_open_cohort(session: Session) -> Optional[Cohort]:
    return session.execute(select(Cohort).where(Cohort.status == "open")).scalars().first()


def get_cohort_by_label(session: Session, label: str) -> Cohort:
    cohort = session.execute(select(Cohort).where(Cohort.label == label)).scalars().first()
    if cohort is None:
        raise NotFoundError(f"No year labelled '{label}'.")
    return cohort


def list_cohorts(session: Session) -> list[dict[str, Any]]:
    cohorts = session.execute(select(Cohort).order_by(Cohort.created_at.desc())).scalars().all()
    out = []
    for c in cohorts:
        groups = session.scalar(select(func.count(Group.id)).where(Group.cohort_id == c.id))
        members = session.scalar(
            select(func.count(Member.id)).join(Group, Member.group_id == Group.id)
            .where(Group.cohort_id == c.id)
        )
        results = session.scalar(
            select(func.count(Result.id)).join(Group, Result.group_id == Group.id)
            .where(Group.cohort_id == c.id)
            .where(Result.deleted_at.is_(None)).where(Result.superseded_by.is_(None))
        )
        created = c.created_at.replace(tzinfo=timezone.utc) if c.created_at.tzinfo is None else c.created_at
        closed = None
        if c.closed_at is not None:
            closed = (c.closed_at.replace(tzinfo=timezone.utc) if c.closed_at.tzinfo is None else c.closed_at).isoformat()
        out.append({"id": c.id, "label": c.label, "status": c.status,
                    "created_at": created.isoformat(), "closed_at": closed,
                    "group_count": groups, "member_count": members, "result_count": results})
    return out


def create_cohort(session: Session, label: str) -> Cohort:
    label = (label or "").strip()
    if not label:
        raise ValidationError("Year label must not be empty.")
    if get_open_cohort(session) is not None:
        raise ConflictError("A year is already open. Close it before opening a new one.")
    if session.execute(select(Cohort).where(Cohort.label == label)).scalars().first():
        raise ConflictError(f"A year labelled '{label}' already exists.")
    cohort = Cohort(label=label, status="open")
    session.add(cohort)
    events.log(session, "cohort_open", actor="admin", detail={"label": label}, commit=False)
    try:
        session.flush()
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Could not open the year (one may already be open).") from exc
    return cohort


def close_open_cohort(session: Session) -> Cohort:
    cohort = get_open_cohort(session)
    if cohort is None:
        raise ConflictError("There is no open year to close.")
    cohort.status = "closed"
    cohort.closed_at = datetime.now(timezone.utc)
    events.log(session, "cohort_close", actor="admin", detail={"label": cohort.label}, commit=False)
    session.commit()
    return cohort
