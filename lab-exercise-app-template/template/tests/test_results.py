"""Durability: append-only, supersede, closed-year rejection, scopes, CSV mirror (§5, §B4, §B6)."""
from __future__ import annotations

import pytest

from core import cohorts, identity, results as R
from core.config import settings
from core.errors import ConflictError, NotFoundError
from tests.conftest import DEFAULT_YEAR, SECOND_YEAR, register_student, valid_measurement


def _submit(session, member, **over):
    return R.submit_result(session, member.id, valid_measurement(**over))


def test_submit_and_latest(session):
    m = register_student(session)
    _submit(session, m, measured_logp=1.5)
    rows = R.query_results(session, latest=True)
    assert len(rows) == 1 and rows[0]["values"]["measured_logp"] == 1.5
    assert rows[0]["superseded"] is False
    assert rows[0]["kuid"] == "abc123" and rows[0]["year"] == DEFAULT_YEAR


def test_supersede_keeps_history(session):
    m = register_student(session)
    first = _submit(session, m, measured_logp=1.5)
    new = R.supersede_result(session, first.id, valid_measurement(measured_logp=2.5))

    latest = R.query_results(session, latest=True)
    assert len(latest) == 1 and latest[0]["values"]["measured_logp"] == 2.5

    history = R.query_results(session, latest=False)
    assert len(history) == 2
    old = next(r for r in history if r["id"] == first.id)
    assert old["superseded"] is True
    assert next(r for r in history if r["id"] == new.id)["superseded"] is False


def test_cannot_supersede_twice(session):
    m = register_student(session)
    first = _submit(session, m)
    R.supersede_result(session, first.id, valid_measurement(measured_logp=2.0))
    with pytest.raises(ConflictError):
        R.supersede_result(session, first.id, valid_measurement(measured_logp=3.0))


def test_closed_year_rejects_writes_but_stays_readable(session):
    m = register_student(session)
    _submit(session, m)
    cohorts.close_open_cohort(session)
    with pytest.raises(ConflictError):
        _submit(session, m)
    # still fully queryable + exportable
    assert len(R.query_results(session, latest=True)) == 1
    # open a new year; the old one persists
    cohorts.create_cohort(session, SECOND_YEAR)
    labels = {c["label"] for c in cohorts.list_cohorts(session)}
    assert {DEFAULT_YEAR, SECOND_YEAR} <= labels


def test_hard_delete_is_single_row_and_excluded(session):
    m = register_student(session)
    r1 = _submit(session, m, compound_name="aspirin")
    _submit(session, m, compound_name="caffeine")
    R.hard_delete_result(session, r1.id)
    rows = R.query_results(session, latest=True)
    assert len(rows) == 1 and rows[0]["values"]["compound_name"] == "caffeine"
    with pytest.raises(NotFoundError):
        R.hard_delete_result(session, 9999)


def test_scopes_filter_correctly(session):
    a = register_student(session, "aaa111", "Ana", 1, "G1")
    cohort = identity.get_open_cohort(session)
    g2 = identity.create_group(session, cohort, 1, "G2")
    b = identity.register(session, "bbb222", "Bo", 1, group_id=g2.id)
    g3 = identity.create_group(session, cohort, 2, "G3")  # different hold
    c = identity.register(session, "ccc333", "Cy", 2, group_id=g3.id)
    for member in (a, b, c):
        _submit(session, member)

    ctx = identity.member_context(session, a)
    assert len(R.results_for_scope(session, ctx, "own")) == 1
    assert len(R.results_for_scope(session, ctx, "group")) == 1
    assert len(R.results_for_scope(session, ctx, "neighbour")) == 2   # G1 + G2
    assert len(R.results_for_scope(session, ctx, "hold")) == 2        # hold 1 only
    assert len(R.results_for_scope(session, ctx, "year")) == 3
    assert len(R.results_for_scope(session, ctx, "all")) == 3


def test_allowed_scopes_cap():
    assert R.allowed_scopes("group") == ["own", "group"]
    assert R.allowed_scopes("all") == R.SCOPE_ORDER


def test_csv_mirror_written_on_every_submission(session):
    m = register_student(session)
    _submit(session, m)
    assert settings.csv_path.exists(), "long-format CSV mirror should exist (§B6)"
    text = settings.csv_path.read_text(encoding="utf-8")
    assert text.splitlines()[0] == ",".join(R.columns())
    assert "aspirin" in text
    _submit(session, m, compound_name="caffeine")
    assert "caffeine" in settings.csv_path.read_text(encoding="utf-8")


def test_anonymised_rows_blank_identity_but_keep_columns(session):
    m = register_student(session)
    _submit(session, m)
    rows = R.query_results(session)
    anon = R.flat_rows(rows, anonymise=True)[0]
    assert anon["kuid"] == "" and anon["group"] == ""
    assert set(anon.keys()) == set(R.columns())  # column stability preserved
