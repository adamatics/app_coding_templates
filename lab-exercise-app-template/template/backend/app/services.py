"""Chassis service layer — the single home of the data-durability rules (spec §5).

Every rule that protects historical data lives here, so there is exactly one place to
audit and one place the tests pin down:

* Students only ever **append**. Corrections supersede; nothing is mutated or removed.
* Writing to a **closed** cohort is rejected (409).
* "Reset" = close the open cohort + open a new one. No function drops historical data.
* The only destructive path is :func:`hard_delete_result`, admin-only and audited.

Routers stay thin: they validate the measurement payload against ``exercise.schema`` and
translate the exceptions below into HTTP status codes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Audit, Cohort, Group, Member, Result


# --- domain exceptions (routers map these to HTTP codes) --------------------
class ServiceError(Exception):
    """Base class; carries an HTTP status and a student-friendly message."""

    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(ServiceError):
    status_code = 404


class ClosedCohortError(ServiceError):
    status_code = 409


class ConflictError(ServiceError):
    status_code = 409


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:  # SQLite hands back naive datetimes; they are UTC.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# --- audit ------------------------------------------------------------------
def record_audit(session: Session, action: str, detail: dict[str, Any] | None = None,
                 actor: str = "admin") -> None:
    session.add(Audit(action=action, detail=detail or {}, actor=actor))


def list_audit(session: Session, limit: int = 200) -> list[dict[str, Any]]:
    rows = session.execute(
        select(Audit).order_by(Audit.created_at.desc()).limit(limit)
    ).scalars().all()
    return [
        {"id": a.id, "action": a.action, "detail": a.detail, "actor": a.actor,
         "created_at": _iso(a.created_at)}
        for a in rows
    ]


# --- cohorts ----------------------------------------------------------------
def get_open_cohort(session: Session) -> Optional[Cohort]:
    return session.execute(
        select(Cohort).where(Cohort.status == "open")
    ).scalars().first()


def require_open_cohort(session: Session) -> Cohort:
    cohort = get_open_cohort(session)
    if cohort is None:
        raise ConflictError("No cohort is currently open. An admin must open one.")
    return cohort


def get_cohort_by_label(session: Session, label: str) -> Cohort:
    cohort = session.execute(
        select(Cohort).where(Cohort.label == label)
    ).scalars().first()
    if cohort is None:
        raise NotFoundError(f"No cohort labelled '{label}'.")
    return cohort


def list_cohorts(session: Session) -> list[dict[str, Any]]:
    """All cohorts, newest first, each with group and (latest) result counts."""
    cohorts = session.execute(
        select(Cohort).order_by(Cohort.created_at.desc())
    ).scalars().all()
    out: list[dict[str, Any]] = []
    for c in cohorts:
        group_count = session.execute(
            select(func.count(Group.id)).where(Group.cohort_id == c.id)
        ).scalar_one()
        result_count = session.execute(
            select(func.count(Result.id))
            .join(Group, Result.group_id == Group.id)
            .where(Group.cohort_id == c.id)
            .where(Result.deleted_at.is_(None))
            .where(Result.superseded_by.is_(None))
        ).scalar_one()
        out.append({
            "id": c.id, "label": c.label, "status": c.status,
            "created_at": _iso(c.created_at), "closed_at": _iso(c.closed_at),
            "group_count": group_count, "result_count": result_count,
        })
    return out


def create_cohort(session: Session, label: str) -> Cohort:
    """Open a new cohort. Fails if one is already open (close it first) or the
    label already exists. The DB also enforces at-most-one-open via a partial index."""
    label = label.strip()
    if not label:
        raise ServiceError("Cohort label must not be empty.")
    if get_open_cohort(session) is not None:
        raise ConflictError("A cohort is already open. Close it before opening a new one.")
    existing = session.execute(select(Cohort).where(Cohort.label == label)).scalars().first()
    if existing is not None:
        raise ConflictError(f"A cohort labelled '{label}' already exists.")
    cohort = Cohort(label=label, status="open")
    session.add(cohort)
    record_audit(session, "cohort_open", {"label": label})
    try:
        session.flush()
        session.commit()
    except IntegrityError as exc:  # defensive: the partial unique index also guards
        session.rollback()
        raise ConflictError("Could not open cohort (a cohort may already be open).") from exc
    return cohort


def close_open_cohort(session: Session) -> Cohort:
    """Close the currently-open cohort. It becomes read-only but stays queryable
    and exportable forever. This is the ONLY 'reset' — nothing is deleted."""
    cohort = get_open_cohort(session)
    if cohort is None:
        raise ConflictError("There is no open cohort to close.")
    cohort.status = "closed"
    cohort.closed_at = datetime.now(timezone.utc)
    record_audit(session, "cohort_close", {"label": cohort.label, "cohort_id": cohort.id})
    session.commit()
    return cohort


# --- groups & members -------------------------------------------------------
def _cohort_of_group(session: Session, group: Group) -> Cohort:
    return session.get(Cohort, group.cohort_id)


def get_group(session: Session, group_id: int) -> Group:
    group = session.get(Group, group_id)
    if group is None:
        raise NotFoundError(f"No group with id {group_id}.")
    return group


def list_groups(session: Session, cohort: Cohort) -> list[dict[str, Any]]:
    groups = session.execute(
        select(Group).where(Group.cohort_id == cohort.id).order_by(Group.name)
    ).scalars().all()
    out = []
    for g in groups:
        members = session.execute(
            select(Member).where(Member.group_id == g.id).order_by(Member.created_at)
        ).scalars().all()
        out.append({
            "id": g.id, "name": g.name, "cohort": cohort.label,
            "created_at": _iso(g.created_at),
            "members": [{"id": m.id, "display_name": m.display_name} for m in members],
        })
    return out


def serialize_group(session: Session, group: Group) -> dict[str, Any]:
    cohort = _cohort_of_group(session, group)
    members = session.execute(
        select(Member).where(Member.group_id == group.id).order_by(Member.created_at)
    ).scalars().all()
    return {
        "id": group.id, "name": group.name, "cohort": cohort.label,
        "created_at": _iso(group.created_at),
        "members": [{"id": m.id, "display_name": m.display_name} for m in members],
    }


def create_group(session: Session, name: str, member_names: list[str]) -> Group:
    """Create a group in the OPEN cohort with initial members. Names are unique
    (case-insensitive) within the cohort."""
    cohort = require_open_cohort(session)
    name = name.strip()
    if not name:
        raise ServiceError("Group name must not be empty.")
    group = Group(cohort_id=cohort.id, name=name, name_key=name.lower())
    session.add(group)
    try:
        session.flush()
        for raw in member_names:
            display = raw.strip()
            if display:
                session.add(Member(group_id=group.id, display_name=display))
        session.commit()
    except IntegrityError as exc:
        # The uniqueness conflict can surface at flush OR at commit (concurrent create).
        session.rollback()
        raise ConflictError(
            f"A group called '{name}' already exists in cohort '{cohort.label}'."
        ) from exc
    return group


def add_member(session: Session, group_id: int, display_name: str) -> Member:
    group = get_group(session, group_id)
    cohort = _cohort_of_group(session, group)
    if cohort.status != "open":
        raise ClosedCohortError(
            f"Cohort '{cohort.label}' is closed; you cannot add members to it."
        )
    display = display_name.strip()
    if not display:
        raise ServiceError("Member name must not be empty.")
    member = Member(group_id=group.id, display_name=display)
    session.add(member)
    session.commit()
    return member


# --- admin group/member management (audited) --------------------------------
def rename_group(session: Session, group_id: int, new_name: str) -> Group:
    group = get_group(session, group_id)
    new_name = new_name.strip()
    if not new_name:
        raise ServiceError("Group name must not be empty.")
    old_name = group.name
    group.name = new_name
    group.name_key = new_name.lower()
    record_audit(session, "group_rename",
                 {"group_id": group_id, "from": old_name, "to": new_name})
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError(
            f"A group called '{new_name}' already exists in that cohort."
        ) from exc
    return group


def merge_groups(session: Session, source_id: int, target_id: int) -> Group:
    """Move all members and results from ``source`` into ``target``, then remove the
    now-empty source group. Results are re-parented, never deleted — history survives."""
    if source_id == target_id:
        raise ServiceError("Cannot merge a group into itself.")
    source = get_group(session, source_id)
    target = get_group(session, target_id)
    if source.cohort_id != target.cohort_id:
        raise ConflictError("Groups must be in the same cohort to merge.")
    session.execute(
        Result.__table__.update().where(Result.group_id == source_id)
        .values(group_id=target_id)
    )
    session.execute(
        Member.__table__.update().where(Member.group_id == source_id)
        .values(group_id=target_id)
    )
    record_audit(session, "group_merge",
                 {"source_id": source_id, "source_name": source.name,
                  "target_id": target_id, "target_name": target.name})
    session.delete(source)
    session.commit()
    return target


def delete_group(session: Session, group_id: int) -> None:
    """Delete a typo group. Refused if it has any (non-deleted) results — use merge for
    a group that already holds data, so history is never destroyed."""
    group = get_group(session, group_id)
    result_count = session.execute(
        select(func.count(Result.id))
        .where(Result.group_id == group_id)
        .where(Result.deleted_at.is_(None))
    ).scalar_one()
    if result_count > 0:
        raise ConflictError(
            f"Group '{group.name}' has {result_count} result(s). Merge it into another "
            "group instead of deleting, so no data is lost."
        )
    record_audit(session, "group_delete", {"group_id": group_id, "name": group.name})
    session.delete(group)  # members cascade
    session.commit()


def delete_member(session: Session, member_id: int) -> None:
    member = session.get(Member, member_id)
    if member is None:
        raise NotFoundError(f"No member with id {member_id}.")
    record_audit(session, "member_delete",
                 {"member_id": member_id, "display_name": member.display_name})
    session.delete(member)
    session.commit()


# --- results (append-only) --------------------------------------------------
def submit_result(session: Session, group_id: int, payload: dict[str, Any]) -> Result:
    """Append a new result for a group. Rejected if the group's cohort is closed."""
    group = get_group(session, group_id)
    cohort = _cohort_of_group(session, group)
    if cohort.status != "open":
        raise ClosedCohortError(
            f"Cohort '{cohort.label}' is closed; results can no longer be submitted."
        )
    result = Result(group_id=group.id, payload=payload)
    session.add(result)
    session.commit()
    return result


def supersede_result(session: Session, old_result_id: int, payload: dict[str, Any]) -> Result:
    """Submit a correction: append a new row and point the old one at it. The old
    row is never edited away — full history is preserved."""
    old = session.get(Result, old_result_id)
    if old is None or old.deleted_at is not None:
        raise NotFoundError(f"No result with id {old_result_id}.")
    if old.superseded_by is not None:
        raise ConflictError(
            "That result has already been corrected. Correct the latest version instead."
        )
    group = get_group(session, old.group_id)
    cohort = _cohort_of_group(session, group)
    if cohort.status != "open":
        raise ClosedCohortError(
            f"Cohort '{cohort.label}' is closed; results can no longer be corrected."
        )
    new = Result(group_id=group.id, payload=payload)
    session.add(new)
    session.flush()  # need new.id
    old.superseded_by = new.id
    session.commit()
    return new


def hard_delete_result(session: Session, result_id: int) -> None:
    """Admin-only removal of a single bogus row. Audited. This is the ONLY destructive
    operation in the whole app, and it never touches more than one row."""
    result = session.get(Result, result_id)
    if result is None:
        raise NotFoundError(f"No result with id {result_id}.")
    result.deleted_at = datetime.now(timezone.utc)
    record_audit(session, "result_hard_delete",
                 {"result_id": result_id, "group_id": result.group_id})
    session.commit()


# --- result queries ---------------------------------------------------------
def _result_row(session: Session, r: Result, group: Group, cohort: Cohort) -> dict[str, Any]:
    return {
        "id": r.id,
        "group_id": group.id,
        "group": group.name,
        "cohort": cohort.label,
        "submitted_at": _iso(r.submitted_at),
        "superseded": r.superseded_by is not None,
        "superseded_by": r.superseded_by,
        "values": r.payload,
    }


def query_results(session: Session, cohort: str = "all", latest: bool = True) -> list[dict[str, Any]]:
    """Read results across cohorts.

    ``cohort``: a cohort label, or ``"all"`` for every cohort (powers the compare view).
    ``latest``: when True, hide superseded rows (the default student view). When False,
    include the full history with a ``superseded`` flag (used by exports).
    Hard-deleted rows are always excluded.
    """
    stmt = (
        select(Result, Group, Cohort)
        .join(Group, Result.group_id == Group.id)
        .join(Cohort, Group.cohort_id == Cohort.id)
        .where(Result.deleted_at.is_(None))
    )
    if cohort != "all":
        stmt = stmt.where(Cohort.label == cohort)
    if latest:
        stmt = stmt.where(Result.superseded_by.is_(None))
    stmt = stmt.order_by(Cohort.created_at, Group.name, Result.submitted_at)
    rows = session.execute(stmt).all()
    return [_result_row(session, r, g, c) for (r, g, c) in rows]


# --- chassis analysis (merged with exercise.analysis in the router) ---------
def chassis_summary(session: Session, cohort: str = "all") -> dict[str, Any]:
    """Exercise-agnostic summary stats the chassis can always compute."""
    rows = query_results(session, cohort=cohort, latest=True)
    groups = {r["group_id"] for r in rows}
    per_cohort: dict[str, int] = {}
    for r in rows:
        per_cohort[r["cohort"]] = per_cohort.get(r["cohort"], 0) + 1
    return {
        "n_results": len(rows),
        "n_groups": len(groups),
        "results_per_cohort": per_cohort,
    }
