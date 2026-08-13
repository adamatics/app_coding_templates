"""Results: append-only submit/supersede/query with scope filtering (CHASSIS, no streamlit).

Durability rules (base spec §5, retained): students only append; a correction *supersedes*;
writes to a closed cohort are rejected; the only destructive op is an admin single-row hard
delete. Every submission also rewrites the long-format CSV mirror (§B6).
"""
from __future__ import annotations

import csv
import io
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import events
from .config import settings
from .errors import ConflictError, NotFoundError, ValidationError
from .exercise_bridge import field_names
from .identity import list_groups, member_context
from .models import Cohort, Group, Member, Result
from .storage import atomic_write_text

# Retrieval scopes, widest last (§B4). ``max_scope`` (course metadata) caps the selector.
SCOPE_ORDER = ["own", "group", "neighbour", "hold", "year", "all"]
# Meta columns appended after the schema columns — stable across cohorts (§B10).
META_COLUMNS = ["year", "hold", "group", "kuid", "submitted_at", "superseded"]


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def allowed_scopes(max_scope: str) -> list[str]:
    max_scope = max_scope if max_scope in SCOPE_ORDER else "all"
    return SCOPE_ORDER[: SCOPE_ORDER.index(max_scope) + 1]


# --- writes (append-only) ---------------------------------------------------
def submit_result(session: Session, member_id: int, payload: dict[str, Any]) -> Result:
    member = session.get(Member, member_id)
    if member is None:
        raise NotFoundError("Your registration was not found. Please register again.")
    group = session.get(Group, member.group_id)
    cohort = session.get(Cohort, group.cohort_id)
    if cohort.status != "open":
        raise ConflictError(f"Year {cohort.label} is closed; results can no longer be submitted.")
    result = Result(member_id=member.id, group_id=group.id, payload=payload)
    session.add(result)
    session.commit()
    rewrite_csv_mirror(session)
    events.log(session, "result_submitted", context=member_context(session, member),
               detail={"result_id": result.id, "values": payload})
    return result


def supersede_result(session: Session, old_result_id: int, payload: dict[str, Any]) -> Result:
    old = session.get(Result, old_result_id)
    if old is None or old.deleted_at is not None:
        raise NotFoundError("That result was not found.")
    if old.superseded_by is not None:
        raise ConflictError("That result was already corrected; correct the latest version.")
    group = session.get(Group, old.group_id)
    cohort = session.get(Cohort, group.cohort_id)
    if cohort.status != "open":
        raise ConflictError(f"Year {cohort.label} is closed; results can no longer be corrected.")
    old_payload = dict(old.payload)
    new = Result(member_id=old.member_id, group_id=old.group_id, payload=payload)
    session.add(new)
    session.flush()
    old.superseded_by = new.id
    session.commit()
    rewrite_csv_mirror(session)
    # The "overwrite" event: which row replaced which, with before/after and the changed fields.
    member = session.get(Member, old.member_id)
    changed = sorted(k for k in set(old_payload) | set(payload)
                     if old_payload.get(k) != payload.get(k))
    events.log(session, "result_superseded", context=member_context(session, member),
               detail={"superseded_result_id": old_result_id, "new_result_id": new.id,
                       "changed_fields": changed, "old_values": old_payload, "new_values": payload})
    return new


def hard_delete_result(session: Session, result_id: int) -> None:
    """Admin-only removal of a single bogus row (audited by the caller)."""
    result = session.get(Result, result_id)
    if result is None:
        raise NotFoundError(f"No result with id {result_id}.")
    payload = dict(result.payload)
    result.deleted_at = datetime.now(timezone.utc)
    session.commit()
    rewrite_csv_mirror(session)
    # The only destructive path in the app — log the row's contents so it is recoverable.
    events.log(session, "result_hard_deleted", level=events.WARNING, actor="admin",
               detail={"result_id": result_id, "member_id": result.member_id,
                       "group_id": result.group_id, "values": payload})


# --- queries ----------------------------------------------------------------
def _row(r: Result, member: Member, group: Group, cohort: Cohort) -> dict[str, Any]:
    return {
        "id": r.id,
        "member_id": member.id,
        "kuid": member.kuid,
        "group_id": group.id,
        "group": group.name,
        "hold": group.hold,
        "year": cohort.label,
        "submitted_at": _iso(r.submitted_at),
        "superseded": r.superseded_by is not None,
        "values": r.payload,
    }


def query_results(session: Session, *, member_ids: Optional[list[int]] = None,
                  group_ids: Optional[list[int]] = None, latest: bool = True,
                  include_deleted: bool = False) -> list[dict[str, Any]]:
    stmt = (
        select(Result, Member, Group, Cohort)
        .join(Member, Result.member_id == Member.id)
        .join(Group, Result.group_id == Group.id)
        .join(Cohort, Group.cohort_id == Cohort.id)
    )
    if not include_deleted:
        stmt = stmt.where(Result.deleted_at.is_(None))
    if latest:
        stmt = stmt.where(Result.superseded_by.is_(None))
    if member_ids is not None:
        stmt = stmt.where(Result.member_id.in_(member_ids or [-1]))
    if group_ids is not None:
        stmt = stmt.where(Result.group_id.in_(group_ids or [-1]))
    stmt = stmt.order_by(Cohort.created_at, Group.name, Result.submitted_at)
    return [_row(r, m, g, c) for (r, m, g, c) in session.execute(stmt).all()]


def neighbour_group_id(session: Session, group_id: int) -> Optional[int]:
    """The adjacent group in the same hold+year (cyclic), or None if the group is alone."""
    group = session.get(Group, group_id)
    if group is None:
        return None
    cohort = session.get(Cohort, group.cohort_id)
    peers = [g.id for g in list_groups(session, cohort, group.hold)]
    if len(peers) < 2:
        return None
    idx = peers.index(group_id)
    return peers[(idx + 1) % len(peers)]


def resolve_scope(session: Session, ctx: dict[str, Any], scope: str) -> dict[str, Any]:
    """Turn a scope + the current member's context into a query filter (§B4)."""
    if scope not in SCOPE_ORDER:
        raise ValidationError(f"Unknown scope '{scope}'.")
    cohort = session.get(Cohort, ctx["cohort_id"])
    if scope == "own":
        return {"member_ids": [ctx["member_id"]]}
    if scope == "group":
        return {"group_ids": [ctx["group_id"]]}
    if scope == "neighbour":
        nb = neighbour_group_id(session, ctx["group_id"])
        return {"group_ids": [ctx["group_id"]] + ([nb] if nb else [])}
    if scope == "hold":
        return {"group_ids": [g.id for g in list_groups(session, cohort, ctx["hold"])]}
    if scope == "year":
        return {"group_ids": [g.id for g in list_groups(session, cohort)]}
    return {}  # "all" — no filter, every cohort


def results_for_scope(session: Session, ctx: dict[str, Any], scope: str,
                      latest: bool = True) -> list[dict[str, Any]]:
    return query_results(session, latest=latest, **resolve_scope(session, ctx, scope))


# --- flattening (CSV mirror + exports share this for column stability) -------
def flat_rows(rows: list[dict[str, Any]], anonymise: bool = False) -> list[dict[str, Any]]:
    """Schema fields + META_COLUMNS. When ``anonymise`` (comparison views), KUID and group
    are blanked but the columns stay put so exports remain concatenable (§B4, §B10)."""
    cols = field_names()
    out: list[dict[str, Any]] = []
    for r in rows:
        row = {c: r["values"].get(c) for c in cols}
        row["year"] = r["year"]
        row["hold"] = r["hold"]
        row["group"] = "" if anonymise else r["group"]
        row["kuid"] = "" if anonymise else r["kuid"]
        row["submitted_at"] = r["submitted_at"]
        row["superseded"] = r["superseded"]
        out.append(row)
    return out


def columns() -> list[str]:
    return field_names() + META_COLUMNS


def rows_to_csv(rows: list[dict[str, Any]], anonymise: bool = False) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns(), extrasaction="ignore")
    writer.writeheader()
    for row in flat_rows(rows, anonymise=anonymise):
        writer.writerow(row)
    return buf.getvalue()


# The mirror is a whole-file rewrite; serialise it so concurrent sessions can't interleave
# a read-then-write and publish a stale snapshot (the write itself is already atomic).
_mirror_lock = threading.Lock()


def rewrite_csv_mirror(session: Session) -> None:
    """Rewrite the long-format CSV mirror of ALL results (full history) atomically (§B6)."""
    with _mirror_lock:
        all_rows = query_results(session, latest=False, include_deleted=False)
        atomic_write_text(settings.csv_path, rows_to_csv(all_rows))
