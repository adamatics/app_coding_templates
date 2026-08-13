"""Admin logic: auth, course settings, group/member management (CHASSIS, no streamlit).

Admin password compared constant-time, fail-closed when unset (base spec §8). Course
metadata (banner, FAQ, permitted scope, course info) lives in a key-value ``setting`` table
(§B6). Group/member edits preserve history: merge re-parents, delete refuses on data.
"""
from __future__ import annotations

import hmac
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import events
from .config import settings
from .errors import ConflictError, NotFoundError, ValidationError
from .models import Group, Member, Result, Setting

# --- course settings defaults (§B6) ----------------------------------------
DEFAULT_SETTINGS: dict[str, Any] = {
    "course_name": settings.exercise_title,
    "instructor": "",
    "material_links": [],   # [{"label": ..., "url": ...}]
    "documents": [],        # [{"label": ..., "url": ...}]
    "banner": "",           # admin message banner shown on every page when non-empty
    "max_scope": "all",     # permitted retrieval scope cap (§B4)
    "faq_md": "## FAQ\n\n_No questions answered yet._",
    "active_layers": {"group": True, "hold": True},  # individual + year are always on
}


# --- admin auth -------------------------------------------------------------
def verify_admin_password(candidate: str) -> bool:
    if not settings.admin_enabled or settings.admin_password is None:
        return False
    return hmac.compare_digest((candidate or "").encode("utf-8"),
                               settings.admin_password.encode("utf-8"))


# --- settings store ---------------------------------------------------------
def get_setting(session: Session, key: str) -> Any:
    row = session.get(Setting, key)
    if row is not None:
        return row.value
    return DEFAULT_SETTINGS.get(key)


def set_setting(session: Session, key: str, value: Any, actor: str = "admin") -> None:
    row = session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value
    events.log(session, "setting_change", actor=actor, detail={"key": key}, commit=False)
    session.commit()


def all_settings(session: Session) -> dict[str, Any]:
    merged = dict(DEFAULT_SETTINGS)
    for row in session.execute(select(Setting)).scalars().all():
        merged[row.key] = row.value
    return merged


def banner(session: Session) -> str:
    return get_setting(session, "banner") or ""


def max_scope(session: Session) -> str:
    return get_setting(session, "max_scope") or "all"


def faq_markdown(session: Session) -> str:
    return get_setting(session, "faq_md") or ""


# --- group / member management (audited; history-preserving) ---------------
def rename_group(session: Session, group_id: int, new_name: str) -> Group:
    group = session.get(Group, group_id)
    if group is None:
        raise NotFoundError(f"No group with id {group_id}.")
    new_name = (new_name or "").strip()
    if not new_name:
        raise ValidationError("Group name must not be empty.")
    old = group.name
    group.name = new_name
    group.name_key = new_name.lower()
    events.log(session, "group_rename", actor="admin",
               detail={"group_id": group_id, "from": old, "to": new_name}, commit=False)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError(f"A group called '{new_name}' already exists this year.") from exc
    return group


def merge_groups(session: Session, source_id: int, target_id: int) -> Group:
    if source_id == target_id:
        raise ValidationError("Cannot merge a group into itself.")
    source = session.get(Group, source_id)
    target = session.get(Group, target_id)
    if source is None or target is None:
        raise NotFoundError("Group not found.")
    if source.cohort_id != target.cohort_id:
        raise ConflictError("Groups must be in the same year to merge.")
    session.execute(Result.__table__.update().where(Result.group_id == source_id).values(group_id=target_id))
    session.execute(Member.__table__.update().where(Member.group_id == source_id).values(group_id=target_id))
    events.log(session, "group_merge", actor="admin",
               detail={"source_id": source_id, "source_name": source.name,
                       "target_id": target_id, "target_name": target.name}, commit=False)
    session.delete(source)
    session.commit()
    return target


def delete_group(session: Session, group_id: int) -> None:
    group = session.get(Group, group_id)
    if group is None:
        raise NotFoundError(f"No group with id {group_id}.")
    n = session.scalar(select(func.count(Result.id)).where(Result.group_id == group_id).where(Result.deleted_at.is_(None)))
    if n:
        raise ConflictError(f"Group '{group.name}' has {n} result(s). Merge it instead, so no data is lost.")
    members = session.execute(select(Member).where(Member.group_id == group_id)).scalars().all()
    for m in members:
        session.delete(m)
    events.log(session, "group_delete", actor="admin",
               detail={"group_id": group_id, "name": group.name}, commit=False)
    session.delete(group)
    session.commit()


def delete_member(session: Session, member_id: int) -> None:
    member = session.get(Member, member_id)
    if member is None:
        raise NotFoundError(f"No member with id {member_id}.")
    n = session.scalar(select(func.count(Result.id)).where(Result.member_id == member_id).where(Result.deleted_at.is_(None)))
    if n:
        raise ConflictError(f"{member.display_name} has {n} result(s); reassign instead of deleting.")
    events.log(session, "member_delete", actor="admin",
               detail={"member_id": member_id, "kuid": member.kuid}, commit=False)
    session.delete(member)
    session.commit()
