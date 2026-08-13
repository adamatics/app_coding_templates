"""Test fixtures. Env is set BEFORE importing core, because core.config reads it at import."""
from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="lab-exercise-test-")
os.environ.setdefault("DATA_DIR", _TMP)          # a mounted, writable "volume"
os.environ.setdefault("ADMIN_PASSWORD", "admin-secret")
os.environ.setdefault("COURSE_PASSWORD", "course-secret")
os.environ.setdefault("DEMO_MODE", "false")

import pytest  # noqa: E402

from core.config import settings  # noqa: E402
from core.db import (  # noqa: E402
    SessionLocal,
    check_schema_version,
    engine,
    require_writable_data_dir,
)
from core.models import Base, Cohort  # noqa: E402

ADMIN_PASSWORD = "admin-secret"
COURSE_PASSWORD = "course-secret"
DEFAULT_YEAR = settings.default_year
SECOND_YEAR = "9999" if DEFAULT_YEAR != "9999" else "9998"


def reset_db() -> None:
    """Leave the database in the same state a real start would (init_db), not just empty."""
    require_writable_data_dir()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        check_schema_version(session)      # records the current schema version, as init_db does
        session.add(Cohort(label=DEFAULT_YEAR, status="open"))
        session.commit()


@pytest.fixture()
def session():
    reset_db()
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def valid_measurement(**overrides):
    """A payload valid against the logP worked example; override per test."""
    payload = {
        "compound_name": "aspirin",
        "database_logp": 1.19,
        "tool_logp": 1.31,
        "measured_logp": 1.24,
        "neighbour_logp": 1.28,
        "method": "shake-flask",
        "temperature_c": 25.0,
        "replicate": 1,
        "measured_on": "2026-09-15",
    }
    payload.update(overrides)
    return payload


def register_student(session, kuid="abc123", name="Ana", hold=1, group="Group 1"):
    from core import identity

    return identity.register(session, kuid, name, hold, new_group_name=group)
