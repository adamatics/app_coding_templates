"""Durable browser sessions without student passwords (CHASSIS, framework-free — no streamlit).

Addendum B §B2 forbids per-student passwords, and Streamlit's ``st.session_state`` is lost on a
page refresh or a new tab. Without something in between, a student who reloads has to re-enter
the course password and their KUID — friction that matters in a lab with flaky wifi, and every
time they come back weeks later to write their report.

So: after the course gate the app puts an **opaque random token** in the URL, and this module
maps it back to (gate passed, which student). Properties that matter:

* **No personal data in the URL.** The token is random, not a signed blob containing the KUID
  — nothing decodable ends up in browser history or proxy logs (KUID is personal data under
  the KU data processing agreement).
* **Only a hash is stored.** A copy of the database yields no usable tokens.
* **Unguessable, so it cannot bypass the course gate.** 256 bits of ``secrets`` entropy; a
  token can only come from someone who actually passed the gate.
* **Expiring and revocable.** Sign-out revokes; expired rows are purged at startup.

Threat model, stated plainly: a student who shares their URL shares their session, exactly as
a student who shares their KUID can already be impersonated (base spec §6, honour system by
design). The token adds no *new* class of risk, but it is a bearer credential — hence the TTL,
the revoke-on-sign-out, and no personal data inside it.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import settings
from .models import Cohort, Group, Member, SessionToken

# 32 bytes -> 43-char urlsafe string. Long enough to be unguessable, short enough for a URL.
_TOKEN_BYTES = 32


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite hands back naive datetimes; they are UTC."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def issue(session: Session, member_id: Optional[int] = None,
          ttl_days: Optional[int] = None) -> str:
    """Create a session and return the RAW token (the only time it exists in plaintext)."""
    raw = secrets.token_urlsafe(_TOKEN_BYTES)
    ttl = settings.session_ttl_days if ttl_days is None else ttl_days
    session.add(SessionToken(
        token_hash=_hash(raw),
        member_id=member_id,
        expires_at=_now() + timedelta(days=ttl),
    ))
    session.commit()
    return raw


def attach_member(session: Session, raw_token: str, member_id: int) -> bool:
    """Bind a gate-only session to a student once they register. Keeps the same URL."""
    row = session.get(SessionToken, _hash(raw_token))
    if row is None:
        return False
    row.member_id = member_id
    row.last_seen_at = _now()
    session.commit()
    return True


def resolve(session: Session, raw_token: str) -> Optional[dict[str, Any]]:
    """Return ``{"gate": True, "member_id": int|None}`` for a valid token, else ``None``.

    A token whose student belongs to a cohort that is no longer open restores the gate but not
    the identity: the year has rolled over, so they register again in the new year rather than
    silently writing to a closed one.
    """
    if not raw_token:
        return None
    row = session.get(SessionToken, _hash(raw_token))
    if row is None:
        return None
    if _aware(row.expires_at) <= _now():
        session.delete(row)
        session.commit()
        return None

    member_id = row.member_id
    if member_id is not None:
        member = session.get(Member, member_id)
        cohort = None
        if member is not None:
            group = session.get(Group, member.group_id)
            cohort = session.get(Cohort, group.cohort_id) if group else None
        if member is None or cohort is None or cohort.status != "open":
            member_id = None  # gate still good; identity must be re-established

    row.last_seen_at = _now()
    session.commit()
    return {"gate": True, "member_id": member_id}


def revoke(session: Session, raw_token: str) -> None:
    """Sign out: the token stops working immediately."""
    row = session.get(SessionToken, _hash(raw_token))
    if row is not None:
        session.delete(row)
        session.commit()


def purge_expired(session: Session) -> int:
    """Delete expired sessions (called at startup). Returns how many were removed."""
    result = session.execute(delete(SessionToken).where(SessionToken.expires_at <= _now()))
    session.commit()
    return int(result.rowcount or 0)


def active_count(session: Session) -> int:
    return len(session.execute(
        select(SessionToken.token_hash).where(SessionToken.expires_at > _now())
    ).all())
