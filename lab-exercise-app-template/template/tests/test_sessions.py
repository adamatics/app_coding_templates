"""Durable browser sessions without student passwords (§B2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core import cohorts, sessions
from core.models import SessionToken
from tests.conftest import SECOND_YEAR, register_student


def test_issue_and_resolve_gate_only(session):
    token = sessions.issue(session)
    state = sessions.resolve(session, token)
    assert state == {"gate": True, "member_id": None}


def test_issue_and_resolve_with_member(session):
    m = register_student(session)
    token = sessions.issue(session, member_id=m.id)
    assert sessions.resolve(session, token) == {"gate": True, "member_id": m.id}


def test_attach_member_upgrades_a_gate_token(session):
    token = sessions.issue(session)
    m = register_student(session)
    assert sessions.attach_member(session, token, m.id) is True
    assert sessions.resolve(session, token)["member_id"] == m.id


def test_raw_token_is_never_stored(session):
    token = sessions.issue(session)
    stored = session.query(SessionToken).all()
    assert len(stored) == 1
    assert stored[0].token_hash != token          # only the hash is persisted
    assert token not in stored[0].token_hash


def test_unknown_and_empty_tokens_resolve_to_none(session):
    assert sessions.resolve(session, "not-a-real-token") is None
    assert sessions.resolve(session, "") is None


def test_expired_token_is_rejected_and_cleaned_up(session):
    token = sessions.issue(session)
    row = session.query(SessionToken).one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    session.commit()
    assert sessions.resolve(session, token) is None
    assert session.query(SessionToken).count() == 0


def test_revoke_signs_out_immediately(session):
    m = register_student(session)
    token = sessions.issue(session, member_id=m.id)
    sessions.revoke(session, token)
    assert sessions.resolve(session, token) is None


def test_token_from_a_closed_year_keeps_gate_but_drops_identity(session):
    """After the year rolls over the student must register again in the new year rather than
    silently writing to a closed one."""
    m = register_student(session)
    token = sessions.issue(session, member_id=m.id)
    cohorts.close_open_cohort(session)
    cohorts.create_cohort(session, SECOND_YEAR)
    state = sessions.resolve(session, token)
    assert state == {"gate": True, "member_id": None}


def test_purge_expired(session):
    keep = sessions.issue(session)
    stale = sessions.issue(session)
    row = session.get(SessionToken, sessions._hash(stale))
    row.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    session.commit()
    assert sessions.purge_expired(session) == 1
    assert sessions.resolve(session, keep) is not None


def test_tokens_are_unique_and_unguessable(session):
    tokens = {sessions.issue(session) for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(t) >= 40 for t in tokens)
