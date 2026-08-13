"""Event logging: registrations, submissions, overwrites, exports, admin actions, errors."""
from __future__ import annotations

import json

from core import admin, cohorts, events, export, identity
from core import results as R
from core.config import settings
from tests.conftest import SECOND_YEAR, register_student, valid_measurement


def _actions(session) -> list[str]:
    return [e["action"] for e in events.recent(session, limit=500)]


# --- the events the instructor asked for -----------------------------------
def test_registration_is_logged_with_datetime_and_identity(session):
    m = register_student(session, "abc123", "Ana", 1, "G1")
    rows = [e for e in events.recent(session) if e["action"] == "student_registered"]
    assert len(rows) == 1
    row = rows[0]
    assert row["kuid"] == "abc123" and row["group"] == "G1" and row["hold"] == 1
    assert row["created_at"]                      # datetime recorded
    assert "Ana" in row["detail"]


def test_returning_student_is_distinguished_from_a_new_one(session):
    register_student(session, "abc123")
    identity.register(session, "abc123", "Ana", 1, new_group_name="G1")
    actions = _actions(session)
    assert actions.count("student_registered") == 1
    assert actions.count("student_returned") == 1


def test_submission_is_logged_with_values(session):
    m = register_student(session)
    R.submit_result(session, m.id, valid_measurement(measured_logp=1.5))
    row = next(e for e in events.recent(session) if e["action"] == "result_submitted")
    assert row["kuid"] == "abc123"
    assert "1.5" in row["detail"]


def test_overwrite_records_old_and_new_values_and_changed_fields(session):
    m = register_student(session)
    first = R.submit_result(session, m.id, valid_measurement(measured_logp=1.0))
    R.supersede_result(session, first.id, valid_measurement(measured_logp=2.0, method="HPLC"))

    row = next(e for e in events.recent(session) if e["action"] == "result_superseded")
    detail = json.loads(row["detail"])
    assert detail["superseded_result_id"] == first.id
    assert set(detail["changed_fields"]) == {"measured_logp", "method"}
    assert detail["old_values"]["measured_logp"] == 1.0
    assert detail["new_values"]["measured_logp"] == 2.0


def test_export_is_logged_only_when_taken(session):
    m = register_student(session)
    R.submit_result(session, m.id, valid_measurement())
    rows = R.query_results(session)
    # Building bytes must NOT log (Streamlit rebuilds them on every rerun) ...
    export.to_csv(rows)
    export.to_excel(rows)
    assert "export_generated" not in _actions(session)
    # ... only an actual download does.
    ctx = identity.member_context(session, m)
    export.log_export(session, "csv", context=ctx, scope="My group's data", rows=len(rows))
    row = next(e for e in events.recent(session) if e["action"] == "export_generated")
    assert "csv" in row["detail"] and row["kuid"] == "abc123"


def test_hard_delete_is_logged_as_a_warning_with_the_values(session):
    m = register_student(session)
    r = R.submit_result(session, m.id, valid_measurement(compound_name="aspirin"))
    R.hard_delete_result(session, r.id)
    row = next(e for e in events.recent(session) if e["action"] == "result_hard_deleted")
    assert row["level"] == events.WARNING
    assert "aspirin" in row["detail"]      # recoverable from the log


def test_admin_actions_are_logged(session):
    admin.set_setting(session, "banner", "Use fridge C")
    cohorts.close_open_cohort(session)
    cohorts.create_cohort(session, SECOND_YEAR)
    actions = _actions(session)
    for expected in ("setting_change", "cohort_close", "cohort_open"):
        assert expected in actions


# --- errors -----------------------------------------------------------------
def test_log_error_captures_type_message_and_traceback(session):
    try:
        raise ValueError("boom while saving")
    except ValueError as exc:
        events.log_error(session, "submission_failed", exc, detail={"page": "capture"})
    row = next(e for e in events.recent(session) if e["action"] == "submission_failed")
    assert row["level"] == events.ERROR
    detail = json.loads(row["detail"])
    assert detail["error_type"] == "ValueError"
    assert "boom while saving" in detail["error"]
    assert "ValueError" in detail["traceback"]


# --- filtering / reading ----------------------------------------------------
def test_recent_filters_by_level_action_and_kuid(session):
    m = register_student(session, "abc123")
    R.submit_result(session, m.id, valid_measurement())
    events.log(session, "custom_warning", level=events.WARNING)

    assert all(e["level"] == events.WARNING
               for e in events.recent(session, level=events.WARNING))
    assert {e["action"] for e in events.recent(session, action="result_submitted")} == {"result_submitted"}
    assert all(e["kuid"] == "abc123" for e in events.recent(session, kuid="ABC123"))
    assert "result_submitted" in events.action_names(session)


# --- the sinks --------------------------------------------------------------
def test_events_are_written_to_the_volume_jsonl(session):
    register_student(session)
    path = settings.app_data_dir / "events.jsonl"
    assert path.exists(), "events should be mirrored to the durable volume log"
    lines = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert any(rec["action"] == "student_registered" for rec in lines)
    assert all("ts" in rec and "app" in rec for rec in lines)


def test_logging_never_breaks_the_caller(session, monkeypatch):
    """A failing sink must not stop a student's submission."""
    def boom(*_args, **_kwargs):
        raise OSError("volume gone")

    monkeypatch.setattr(events, "_to_volume", boom)
    monkeypatch.setattr(events, "_to_stdout", boom)
    m = register_student(session)
    # Must not raise even though both non-DB sinks are broken.
    result = R.submit_result(session, m.id, valid_measurement())
    assert result.id is not None


def test_stdout_omits_kuid_unless_log_pii(monkeypatch, caplog):
    """Aggregated container logs get a pseudonymous actor; the KUID stays in the DB/volume."""
    monkeypatch.delenv("LOG_PII", raising=False)
    with caplog.at_level("INFO", logger="labapp.events"):
        events._to_stdout({"level": "info", "action": "x", "actor": "abc123",
                           "kuid": "abc123", "member_id": 7})
    emitted = "\n".join(r.getMessage() for r in caplog.records)
    assert "abc123" not in emitted
    assert "member:7" in emitted


def test_stdout_includes_kuid_when_log_pii_enabled(monkeypatch, caplog):
    monkeypatch.setenv("LOG_PII", "true")
    with caplog.at_level("INFO", logger="labapp.events"):
        events._to_stdout({"level": "info", "action": "x", "actor": "abc123",
                           "kuid": "abc123", "member_id": 7})
    assert "abc123" in "\n".join(r.getMessage() for r in caplog.records)
