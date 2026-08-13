"""Identity: KUID format, course gate, registration, reassignment (§B2, §B10)."""
from __future__ import annotations

import pytest

from core import admin, identity
from core.config import settings
from core.errors import ConflictError, ValidationError
from tests.conftest import COURSE_PASSWORD, register_student


def test_kuid_format_validation():
    assert identity.normalize_kuid("ABC123") == "abc123"
    for bad in ["ab123", "abcd123", "abc12", "abc1234", "123abc", "", "ab-123"]:
        with pytest.raises(ValidationError):
            identity.normalize_kuid(bad)


def test_course_gate_rejects_wrong_admits_right():
    assert identity.check_course_password("nope") is False
    assert identity.check_course_password(COURSE_PASSWORD) is True


def test_course_gate_fails_closed_when_unset():
    original = settings.course_password
    object.__setattr__(settings, "course_password", None)
    try:
        assert settings.gate_enabled is False
        assert identity.check_course_password("anything") is False
        assert identity.check_course_password("") is False
    finally:
        object.__setattr__(settings, "course_password", original)


def test_register_creates_group_and_is_idempotent(session):
    m1 = register_student(session, "abc123", "Ana", 1, "Group 1")
    ctx = identity.member_context(session, m1)
    assert ctx["kuid"] == "abc123" and ctx["group"] == "Group 1" and ctx["hold"] == 1
    # Returning later with the same KUID recognises the student (no password needed).
    m2 = identity.register(session, "ABC123", "Ana", 1, new_group_name="Group 1")
    assert m2.id == m1.id


def test_join_existing_group(session):
    first = register_student(session, "abc123", "Ana", 1, "Group 1")
    cohort = identity.get_open_cohort(session)
    groups = identity.list_groups(session, cohort, hold=1)
    second = identity.register(session, "xyz789", "Bo", 1, group_id=groups[0].id)
    assert second.group_id == first.group_id


def test_duplicate_group_name_rejected(session):
    register_student(session, "abc123", "Ana", 1, "Group 1")
    cohort = identity.get_open_cohort(session)
    with pytest.raises(ConflictError):
        identity.create_group(session, cohort, 1, "group 1")  # case-insensitive


def test_admin_can_reassign(session):
    m = register_student(session, "abc123", "Ana", 1, "Group 1")
    cohort = identity.get_open_cohort(session)
    other = identity.create_group(session, cohort, 2, "Group 2")
    identity.reassign_member(session, m.id, other.id)
    ctx = identity.member_context(session, m)
    assert ctx["group"] == "Group 2" and ctx["hold"] == 2


def test_admin_password_fail_closed():
    original = settings.admin_password
    object.__setattr__(settings, "admin_password", None)
    try:
        assert settings.admin_enabled is False
        assert admin.verify_admin_password("anything") is False
    finally:
        object.__setattr__(settings, "admin_password", original)
