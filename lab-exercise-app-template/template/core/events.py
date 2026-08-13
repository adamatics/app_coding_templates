"""Event logging (CHASSIS, framework-free — imports streamlit NOWHERE).

Records the things a teacher or an operator actually needs after a lab session:

* **who appeared** — registrations and returning students, with timestamps
* **what was entered** — every submission
* **what was overwritten** — corrections (supersedes), with the old and new values
* **what was taken out** — exports (format, scope, row count)
* **what went wrong** — errors, with exception type, message and a trimmed traceback
* plus every admin action (login, cohort open/close, group edits, hard deletes, settings)

Three sinks, because each answers a different question:

1. **The ``event`` table** — queryable, shown in the admin Log tab, exportable as CSV. This is
   the teacher-facing record.
2. **stdout** via ``logging`` — lands in the container/AdaLab log viewer, where an operator
   looks when the app misbehaves.
3. **``events.jsonl`` on the shared volume** — survives container restarts and redeploys, which
   stdout does not. Size-rotated so it cannot grow without bound.

Two rules this module holds to:

* **Logging must never break the app.** Every sink is wrapped; a failing log cannot stop a
  student's submission. The worst case is a lost log line, never a lost measurement.
* **Personal data stays in the trusted sinks.** The KUID goes to the database and the volume
  file (same data processing agreement as the results themselves). stdout gets a pseudonymous
  ``member_id`` unless ``LOG_PII=true``, because platform logs are aggregated more widely.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Event

INFO = "info"
WARNING = "warning"
ERROR = "error"

# Rotate the volume log at this size (bytes) to keep a semester's worth bounded.
_MAX_LOG_BYTES = 5 * 1024 * 1024
_file_lock = threading.Lock()

_logger = logging.getLogger("labapp.events")
_logger_ready = False


def _log_pii() -> bool:
    return os.environ.get("LOG_PII", "").strip().lower() in {"1", "true", "yes", "on"}


def setup_logging(level: str = "INFO") -> None:
    """Attach a stdout handler once (idempotent). Called from preflight and the app bootstrap."""
    global _logger_ready
    if _logger_ready:
        return
    root = logging.getLogger("labapp")
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"))
        root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.propagate = False
    _logger_ready = True


def _to_stdout(record: dict[str, Any]) -> None:
    try:
        setup_logging()
        safe = {k: v for k, v in record.items() if v is not None}
        if not _log_pii():
            safe.pop("kuid", None)          # pseudonymous in aggregated logs
            if safe.get("actor") not in (None, "admin", "system"):
                safe["actor"] = f"member:{record.get('member_id')}"
        line = json.dumps(safe, default=str, sort_keys=True)
        level = record.get("level", INFO)
        if level == ERROR:
            _logger.error(line)
        elif level == WARNING:
            _logger.warning(line)
        else:
            _logger.info(line)
    except Exception:  # pragma: no cover - logging must never raise
        pass


def _to_volume(record: dict[str, Any]) -> None:
    """Append one JSON line to the durable log on the shared volume, with size rotation."""
    try:
        path = settings.app_data_dir / "events.jsonl"
        with _file_lock:
            try:
                if path.exists() and path.stat().st_size > _MAX_LOG_BYTES:
                    path.replace(path.with_suffix(".jsonl.1"))
            except OSError:
                pass
            # O_APPEND: safe for concurrent single-line appends from many sessions.
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, default=str, sort_keys=True) + "\n")
    except Exception:  # pragma: no cover - a full/absent disk must not break a submission
        pass


def log(session: Optional[Session], action: str, *, level: str = INFO,
        actor: Optional[str] = None, context: Optional[dict[str, Any]] = None,
        detail: Optional[dict[str, Any]] = None, commit: bool = True) -> None:
    """Record an event to all three sinks.

    ``context`` is an identity context dict as returned by ``identity.member_context`` (any
    subset is fine); ``detail`` is free-form JSON describing what happened. ``session`` may be
    None to log to stdout/file only (e.g. before the database exists).
    """
    ctx = context or {}
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "app": settings.project_slug,
        "level": level,
        "action": action,
        "actor": actor or ctx.get("kuid") or "system",
        "member_id": ctx.get("member_id"),
        "kuid": ctx.get("kuid"),
        "group_id": ctx.get("group_id"),
        "group_name": ctx.get("group"),
        "hold": ctx.get("hold"),
        "year": ctx.get("year"),
        "detail": detail or {},
    }

    # Defence in depth: each sink guards itself, and the call site guards them again. A
    # broken or replaced sink must never be able to stop a student's submission.
    for sink in (_to_stdout, _to_volume):
        try:
            sink(record)
        except Exception:  # pragma: no cover
            pass

    if session is None:
        return
    try:
        session.add(Event(
            level=level, action=action, actor=record["actor"],
            member_id=record["member_id"], kuid=record["kuid"],
            group_id=record["group_id"], group_name=record["group_name"],
            hold=record["hold"], year=record["year"], detail=record["detail"],
        ))
        if commit:
            session.commit()
    except Exception:  # pragma: no cover - never let logging break the caller
        try:
            session.rollback()
        except Exception:
            pass


def log_error(session: Optional[Session], action: str, exc: BaseException, *,
              context: Optional[dict[str, Any]] = None,
              detail: Optional[dict[str, Any]] = None) -> None:
    """Record an exception: type, message and a trimmed traceback (last frames only)."""
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    payload = dict(detail or {})
    payload.update({
        "error_type": type(exc).__name__,
        "error": str(exc)[:500],
        "traceback": tb[-2000:],
    })
    log(session, action, level=ERROR, context=context, detail=payload)


# --- reading (admin Log tab, exports) --------------------------------------
def recent(session: Session, limit: int = 500, level: Optional[str] = None,
           action: Optional[str] = None, kuid: Optional[str] = None) -> list[dict[str, Any]]:
    stmt = select(Event).order_by(Event.created_at.desc(), Event.id.desc())
    if level:
        stmt = stmt.where(Event.level == level)
    if action:
        stmt = stmt.where(Event.action == action)
    if kuid:
        stmt = stmt.where(Event.kuid == kuid.lower())
    rows = session.execute(stmt.limit(limit)).scalars().all()
    out = []
    for e in rows:
        created = e.created_at.replace(tzinfo=timezone.utc) if e.created_at.tzinfo is None else e.created_at
        out.append({
            "created_at": created.isoformat(), "level": e.level, "action": e.action,
            "actor": e.actor, "kuid": e.kuid, "group": e.group_name, "hold": e.hold,
            "year": e.year, "detail": json.dumps(e.detail, default=str),
        })
    return out


def action_names(session: Session) -> list[str]:
    return sorted({a for (a,) in session.execute(select(Event.action).distinct()).all()})


def counts_by_action(session: Session) -> dict[str, int]:
    result: dict[str, int] = {}
    for (action,) in session.execute(select(Event.action)).all():
        result[action] = result.get(action, 0) + 1
    return result
