"""The seam contract, course settings, cohort lifecycle and demo seed."""
from __future__ import annotations

import pytest

from core import admin, analysis, cohorts, exercise_bridge, identity
from core import results as R
from core.errors import ConflictError, ValidationError
from tests.conftest import DEFAULT_YEAR, SECOND_YEAR, register_student, valid_measurement


# --- seam ------------------------------------------------------------------
def test_schema_drives_columns():
    fields = exercise_bridge.field_names()
    assert fields[0] == "compound_name"
    assert R.columns() == fields + R.META_COLUMNS


def test_numeric_fields_are_chart_candidates():
    numeric = set(exercise_bridge.numeric_field_names())
    assert {"database_logp", "tool_logp", "measured_logp", "neighbour_logp",
            "temperature_c", "replicate"} <= numeric
    assert numeric.isdisjoint({"compound_name", "method", "measured_on", "notes"})


def test_validation_rejects_bad_payloads():
    with pytest.raises(ValidationError):
        exercise_bridge.validate_payload(valid_measurement(measured_logp=99))
    with pytest.raises(ValidationError):
        exercise_bridge.validate_payload(valid_measurement(method="telepathy"))
    bad = valid_measurement()
    del bad["compound_name"]
    with pytest.raises(ValidationError):
        exercise_bridge.validate_payload(bad)


def test_content_sections_split_instructions_and_questions():
    instructions, questions = exercise_bridge.content_sections()
    assert "logP" in instructions
    assert len(questions) >= 3
    assert questions[0]["id"] == "q1" and questions[0]["prompt"]


# --- course settings (§B6) --------------------------------------------------
def test_settings_defaults_and_override(session):
    assert admin.max_scope(session) == "all"
    assert admin.banner(session) == ""
    admin.set_setting(session, "banner", "Use fridge C, A is broken")
    admin.set_setting(session, "max_scope", "hold")
    assert admin.banner(session) == "Use fridge C, A is broken"
    assert admin.max_scope(session) == "hold"
    assert R.allowed_scopes(admin.max_scope(session)) == ["own", "group", "neighbour", "hold"]


def test_faq_setting(session):
    admin.set_setting(session, "faq_md", "## FAQ\n\n**Q** answer")
    assert "answer" in admin.faq_markdown(session)


# --- cohorts ---------------------------------------------------------------
def test_only_one_open_year(session):
    with pytest.raises(ConflictError):
        cohorts.create_cohort(session, SECOND_YEAR)
    cohorts.close_open_cohort(session)
    cohorts.create_cohort(session, SECOND_YEAR)
    rows = {c["label"]: c for c in cohorts.list_cohorts(session)}
    assert rows[DEFAULT_YEAR]["status"] == "closed"
    assert rows[SECOND_YEAR]["status"] == "open"


def test_cohort_counts(session):
    m = register_student(session)
    R.submit_result(session, m.id, valid_measurement())
    row = next(c for c in cohorts.list_cohorts(session) if c["label"] == DEFAULT_YEAR)
    assert row["group_count"] == 1 and row["member_count"] == 1 and row["result_count"] == 1


# --- admin group ops --------------------------------------------------------
def test_merge_preserves_results(session):
    a = register_student(session, "aaa111", "Ana", 1, "G1")
    cohort = identity.get_open_cohort(session)
    g2 = identity.create_group(session, cohort, 1, "G2")
    b = identity.register(session, "bbb222", "Bo", 1, group_id=g2.id)
    R.submit_result(session, a.id, valid_measurement())
    R.submit_result(session, b.id, valid_measurement())
    admin.merge_groups(session, g2.id, a.group_id)
    rows = R.query_results(session, latest=False)
    assert len(rows) == 2 and {r["group"] for r in rows} == {"G1"}


def test_delete_group_with_results_refused(session):
    a = register_student(session, "aaa111", "Ana", 1, "G1")
    R.submit_result(session, a.id, valid_measurement())
    with pytest.raises(ConflictError):
        admin.delete_group(session, a.group_id)


# --- chassis analysis -------------------------------------------------------
def test_summary_is_anonymised(session):
    m = register_student(session)
    R.submit_result(session, m.id, valid_measurement(measured_logp=2.0))
    rows = R.query_results(session)
    stats = analysis.summarize(rows)
    assert stats["n"] == 1 and "measured_logp" in stats["fields"]
    df = analysis.to_dataframe(rows, anonymise=True)
    assert (df["kuid"] == "").all() and (df["group"] == "").all()


# --- demo seed --------------------------------------------------------------
def test_demo_seed_creates_prior_years(session):
    from core.seed_demo import seed_demo_data

    created = seed_demo_data(session)
    assert set(created) == {"2024", "2025"}
    labels = {c["label"]: c for c in cohorts.list_cohorts(session)}
    assert labels["2024"]["status"] == "closed" and labels["2024"]["result_count"] > 0
    # idempotent
    assert seed_demo_data(session) == []
