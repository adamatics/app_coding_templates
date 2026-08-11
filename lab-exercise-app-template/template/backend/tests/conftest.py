"""Test fixtures. Env is set here BEFORE any app import, because ``config.settings``
reads the environment once at import time."""
from __future__ import annotations

import os
import tempfile

# A throwaway DATA_DIR and a known admin password for the whole test session.
_TMP = tempfile.mkdtemp(prefix="lab-exercise-test-")
os.environ.setdefault("DATA_DIR", _TMP)
os.environ.setdefault("ADMIN_PASSWORD", "test-secret")
os.environ.setdefault("DEMO_MODE", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Cohort  # noqa: E402

ADMIN_PASSWORD = "test-secret"
# The stamped default cohort label, and a guaranteed-different second label. Using these
# (instead of hard-coded "2026-fall") keeps the shipped tests green for ANY value the app
# author chose for default_cohort_label at stamp time.
DEFAULT_COHORT = settings.default_cohort_label
SECOND_COHORT = "cohort-two" if DEFAULT_COHORT != "cohort-two" else "cohort-three"


def _reset_db() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        session.add(Cohort(label=settings.default_cohort_label, status="open"))
        session.commit()


@pytest.fixture()
def client():
    _reset_db()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    _reset_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def admin_client(client):
    """A client with an active admin session."""
    resp = client.post("/api/admin/login", json={"password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    return client


def valid_measurement(**overrides):
    """A payload valid against the worked-example schema; override fields per test."""
    payload = {
        "sample_id": "A1",
        "buffer": "PBS",
        "temperature_c": 25.0,
        "absorbance_au": 0.42,
        "dilution_factor": 1.0,
        "replicate": 1,
        "measured_on": "2026-09-15",
    }
    payload.update(overrides)
    return payload
