"""Identity: KUID, the course-password gate, registration and reassignment (§B2).

CHASSIS, framework-free (no streamlit). No per-student passwords; identity is a KUID
(3 letters + 3 digits) plus a display name and a hold, then join/create a group.
"""
from __future__ import annotations

import hmac
import re
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import events
from .config import settings
from .errors import ConflictError, NotFoundError, ValidationError
from .models import Cohort, Group, Member

KUID_RE = re.compile(r"^[A-Za-z]{3}[0-9]{3}$")


def normalize_kuid(raw: str) -> str:
    """Validate and normalise a KUID (3 letters + 3 digits). Raises ValidationError."""
    value = (raw or "").strip()
    if not KUID_RE.match(value):
        raise ValidationError("KUID must be three letters followed by three digits, e.g. abc123.")
    return value.lower()


# --- course gate ------------------------------------------------------------
def check_course_password(candidate: str) -> bool:
    """Constant-time check of the course password. Fails closed if the gate is unconfigured."""
    if not settings.gate_enabled or settings.course_password is None:
        return False
    return hmac.compare_digest((candidate or "").encode("utf-8"),
                               settings.course_password.encode("utf-8"))


# --- lookup / registration --------------------------------------------------
def get_open_cohort(session: Session) -> Cohort:
    cohort = session.execute(select(Cohort).where(Cohort.status == "open")).scalars().first()
    if cohort is None:
        raise ConflictError("No cohort (year) is currently open. An admin must open one.")
    return cohort


def find_member(session: Session, cohort: Cohort, kuid: str) -> Optional[Member]:
    """The member for this KUID in the given cohort, if already registered."""
    return session.execute(
        select(Member)
        .join(Group, Member.group_id == Group.id)
        .where(Group.cohort_id == cohort.id)
        .where(Member.kuid_key == kuid.lower())
    ).scalars().first()


def list_groups(session: Session, cohort: Cohort, hold: Optional[int] = None) -> list[Group]:
    stmt = select(Group).where(Group.cohort_id == cohort.id)
    if hold is not None:
        stmt = stmt.where(Group.hold == hold)
    return list(session.execute(stmt.order_by(Group.name)).scalars().all())


def create_group(session: Session, cohort: Cohort, hold: int, name: str) -> Group:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Group name must not be empty.")
    if cohort.status != "open":
        raise ConflictError("This year is closed; new groups can't be created.")
    group = Group(cohort_id=cohort.id, hold=hold, name=name, name_key=name.lower())
    session.add(group)
    try:
        session.flush()
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError(f"A group called '{name}' already exists this year.") from exc
    events.log(session, "group_created",
               detail={"group_id": group.id, "name": name, "hold": hold, "year": cohort.label})
    return group


def register(session: Session, kuid: str, display_name: str, hold: int,
             group_id: Optional[int] = None, new_group_name: Optional[str] = None) -> Member:
    """Register an individual in the open cohort and attach them to a group.

    If the KUID is already registered this year, returns the existing member (recognised —
    this is how a student returns weeks later without a password).
    """
    kuid = normalize_kuid(kuid)
    display_name = (display_name or "").strip()
    if not display_name:
        raise ValidationError("Please enter your name.")
    cohort = get_open_cohort(session)

    existing = find_member(session, cohort, kuid)
    if existing is not None:
        events.log(session, "student_returned", context=member_context(session, existing))
        return existing

    if group_id is not None:
        group = session.get(Group, group_id)
        if group is None or group.cohort_id != cohort.id:
            raise NotFoundError("That group was not found in the current year.")
    elif new_group_name:
        group = create_group(session, cohort, hold, new_group_name)
    else:
        raise ValidationError("Choose a group to join or create a new one.")

    member = Member(group_id=group.id, cohort_id=cohort.id, kuid=kuid, kuid_key=kuid.lower(),
                    display_name=display_name)
    session.add(member)
    try:
        session.commit()
    except IntegrityError:
        # Lost a race with another tab/click for the same KUID: the uniqueness constraint did
        # its job. Return the registration that won rather than showing the student an error.
        session.rollback()
        winner = find_member(session, cohort, kuid)
        if winner is None:  # pragma: no cover - constraint fired for some other reason
            raise
        events.log(session, "student_returned", context=member_context(session, winner))
        return winner
    # "User creation" with its datetime — the event carries created_at plus full identity.
    events.log(session, "student_registered", context=member_context(session, member),
               detail={"display_name": display_name, "joined_existing_group": group_id is not None})
    return member


def reassign_member(session: Session, member_id: int, new_group_id: int) -> Member:
    """Admin moves an individual to another group **within the same year** (§B2).

    Cross-year moves are rejected: a student who appears in two years is two registrations,
    not one member teleported between them. Allowing it would leave their results stranded in
    the old year (results carry their own group snapshot) and break every scope query.
    """
    member = session.get(Member, member_id)
    if member is None:
        raise NotFoundError(f"No member with id {member_id}.")
    group = session.get(Group, new_group_id)
    if group is None:
        raise NotFoundError(f"No group with id {new_group_id}.")
    current = session.get(Group, member.group_id)
    if current is not None and current.cohort_id != group.cohort_id:
        raise ConflictError(
            "A student can only be moved between groups in the same year. To place them in "
            "another year, register them there instead."
        )
    old_group_id = member.group_id
    member.group_id = new_group_id
    session.commit()
    events.log(session, "member_reassigned", actor="admin",
               context=member_context(session, member),
               detail={"member_id": member_id, "from_group_id": old_group_id,
                       "to_group_id": new_group_id})
    return member


def member_context(session: Session, member: Member) -> dict:
    """The four identity levels for a member (§B2): kuid, group, hold, year."""
    group = session.get(Group, member.group_id)
    cohort = session.get(Cohort, group.cohort_id)
    return {
        "member_id": member.id,
        "kuid": member.kuid,
        "display_name": member.display_name,
        "group_id": group.id,
        "group": group.name,
        "hold": group.hold,
        "year": cohort.label,
        "cohort_id": cohort.id,
    }
