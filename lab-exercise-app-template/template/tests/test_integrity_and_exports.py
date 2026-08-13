"""Schema integrity guarantees and the wider export surface (post-B review)."""
from __future__ import annotations

import io
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import pytest

from core import admin, cohorts, db, events, export, identity
from core import results as R
from core.db import SessionLocal
from core.errors import ConflictError
from core.models import SCHEMA_VERSION, Member, Setting
from tests.conftest import DEFAULT_YEAR, SECOND_YEAR, register_student, reset_db, valid_measurement


# --- identity integrity -----------------------------------------------------
def test_one_registration_per_kuid_per_year_is_enforced_by_the_database(session):
    """The DB, not just the lookup in register(), guarantees this."""
    register_student(session, "abc123", "Ana", 1, "G1")
    cohort = identity.get_open_cohort(session)
    other = identity.create_group(session, cohort, 1, "G2")
    duplicate = Member(group_id=other.id, cohort_id=cohort.id, kuid="abc123",
                       kuid_key="abc123", display_name="Impostor")
    session.add(duplicate)
    with pytest.raises(Exception):          # IntegrityError from the unique constraint
        session.commit()
    session.rollback()


def test_same_kuid_may_register_again_in_a_later_year(session):
    register_student(session, "abc123", "Ana", 1, "G1")
    cohorts.close_open_cohort(session)
    cohorts.create_cohort(session, SECOND_YEAR)
    m2 = identity.register(session, "abc123", "Ana", 1, new_group_name="G1")
    assert identity.member_context(session, m2)["year"] == SECOND_YEAR


def test_concurrent_registration_of_one_kuid_yields_one_member():
    """Two tabs, one impatient student: one member row, and nobody sees an error."""
    reset_db()
    with SessionLocal() as s:
        cohort = identity.get_open_cohort(s)
        gid = identity.create_group(s, cohort, 1, "Bench 4").id

    def reg(_i):
        with SessionLocal() as s:
            return identity.register(s, "abc123", "Ana", 1, group_id=gid).id

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(reg, range(8)))

    assert len(set(ids)) == 1, "one student must map to exactly one member row"
    with SessionLocal() as s:
        assert s.query(Member).filter(Member.kuid_key == "abc123").count() == 1


def test_reassignment_across_years_is_refused(session):
    m = register_student(session, "abc123", "Ana", 1, "G1")
    cohorts.close_open_cohort(session)
    new_year = cohorts.create_cohort(session, SECOND_YEAR)
    target = identity.create_group(session, new_year, 1, "NewGroup")
    with pytest.raises(ConflictError):
        identity.reassign_member(session, m.id, target.id)
    assert identity.member_context(session, m)["year"] == DEFAULT_YEAR


def test_reassignment_within_a_year_works_and_is_logged(session):
    m = register_student(session, "abc123", "Ana", 1, "G1")
    cohort = identity.get_open_cohort(session)
    target = identity.create_group(session, cohort, 2, "G2")
    identity.reassign_member(session, m.id, target.id)
    ctx = identity.member_context(session, m)
    assert ctx["group"] == "G2" and ctx["hold"] == 2
    assert any(e["action"] == "member_reassigned" for e in events.recent(session))


# --- schema versioning ------------------------------------------------------
def test_schema_version_is_recorded_on_a_fresh_database(session):
    assert session.get(Setting, db.SCHEMA_VERSION_KEY).value == SCHEMA_VERSION


def test_mismatched_schema_version_refuses_to_start(session, monkeypatch):
    session.get(Setting, db.SCHEMA_VERSION_KEY).value = SCHEMA_VERSION - 1
    session.commit()
    monkeypatch.delenv("ALLOW_SCHEMA_MISMATCH", raising=False)
    with pytest.raises(db.SchemaVersionError) as exc:
        db.check_schema_version(session)
    assert str(SCHEMA_VERSION) in str(exc.value)
    assert "backup" in str(exc.value).lower()      # tells the operator what to do first


def test_schema_mismatch_override(session, monkeypatch):
    session.get(Setting, db.SCHEMA_VERSION_KEY).value = SCHEMA_VERSION - 1
    session.commit()
    monkeypatch.setenv("ALLOW_SCHEMA_MISMATCH", "1")
    db.check_schema_version(session)               # does not raise
    assert session.get(Setting, db.SCHEMA_VERSION_KEY).value == SCHEMA_VERSION


# --- wider exports ----------------------------------------------------------
def _seed_with_answers(session):
    from core.models import Answer

    m = register_student(session, "abc123", "Ana", 1, "G1")
    R.submit_result(session, m.id, valid_measurement())
    session.add(Answer(group_id=m.group_id, question_id="q1", text="They agree closely."))
    session.commit()
    return m


def test_answers_export_carries_the_question_text(session):
    _seed_with_answers(session)
    frame = pd.read_csv(io.BytesIO(export.to_answers_csv(session)))
    assert list(frame.columns) == export.ANSWER_COLUMNS
    row = frame.iloc[0]
    assert row["answer"] == "They agree closely."
    assert row["question"]                      # resolved from content.md, not just an id
    assert row["group"] == "G1" and str(row["year"]) == DEFAULT_YEAR


def test_roster_export_lists_who_was_registered(session):
    _seed_with_answers(session)
    rows = export.roster_rows(session)
    assert len(rows) == 1
    assert rows[0]["kuid"] == "abc123" and rows[0]["display_name"] == "Ana"
    assert rows[0]["registered_at"]


def test_full_workbook_has_every_sheet(session):
    _seed_with_answers(session)
    data = export.build_workbook(session, R.query_results(session))
    sheets = pd.read_excel(io.BytesIO(data), sheet_name=None)
    assert set(sheets) == {"results", "answers", "roster", "years", "log"}
    assert not sheets["results"].empty and not sheets["answers"].empty
    assert not sheets["roster"].empty and not sheets["years"].empty


def test_sqlite_backup_is_a_readable_database(session):
    _seed_with_answers(session)
    blob = export.backup_sqlite()
    assert blob.startswith(b"SQLite format 3")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "b.sqlite"
        path.write_bytes(blob)
        con = sqlite3.connect(path)
        try:
            names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert {"result", "member", "cohort", "answer", "event"} <= names
            assert con.execute("SELECT count(*) FROM result").fetchone()[0] == 1
        finally:
            con.close()


def test_admin_export_logging_helper_records_the_actor(session):
    export.log_export(session, "workbook", actor="admin", scope="All years", rows=3)
    row = next(e for e in events.recent(session) if e["action"] == "export_generated")
    assert row["actor"] == "admin" and "workbook" in row["detail"]
