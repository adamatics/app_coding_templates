"""Startup preflight — run BEFORE Streamlit starts (CHASSIS, framework-free).

Fail-loud storage (§A3) has to happen in the *entrypoint*, not lazily on first page render:
Streamlit would otherwise bind the port and happily serve an app whose writes all fail, which
is exactly the "looks fine in the classroom, loses a year of data" failure mode. The
Containerfile runs ``python -m core.preflight`` and only execs streamlit if it exits 0.

Also usable locally:  python -m core.preflight
"""
from __future__ import annotations

import sys

from . import events, sessions
from .config import settings
from .db import SchemaVersionError, StorageError, init_db
from .seed_demo import seed_demo_data


def main() -> int:
    events.setup_logging()
    try:
        init_db()   # verifies the mounted volume + schema, creates tables + the first year
    except SchemaVersionError as exc:
        sys.stderr.write(f"\n=== STARTUP ABORTED: schema mismatch ===\n{exc}\n\n")
        return 1
    except StorageError as exc:
        sys.stderr.write(
            "\n=== STARTUP ABORTED: storage is not usable ===\n"
            f"{exc}\n"
            "Refusing to start so that student data is never written to disposable\n"
            "container-local storage (it would be lost on the next redeploy).\n\n"
        )
        return 1
    except Exception as exc:  # pragma: no cover - unexpected, still fail loudly
        sys.stderr.write(f"\n=== STARTUP ABORTED: {type(exc).__name__}: {exc} ===\n")
        return 1

    from .db import SessionLocal

    if settings.preview_mode:
        sys.stderr.write(
            "\n=== PREVIEW MODE — NOT FOR STUDENTS ===\n"
            f"No volume is mounted at the configured DATA_DIR, so the app is running on\n"
            f"scratch space at {settings.data_dir}. Anything written here is LOST when the\n"
            "container stops.\n"
            "This is allowed only because COURSE_PASSWORD is unset, so no student can sign\n"
            "in and nothing can be collected. Set COURSE_PASSWORD and mount the Shared\n"
            "Volume before using this with a class — the app will then refuse to start\n"
            "without the volume.\n\n"
        )

    if settings.demo_mode:
        with SessionLocal() as session:
            created = seed_demo_data(session)
        if created:
            sys.stdout.write(f"[preflight] seeded demo years: {', '.join(created)}\n")

    with SessionLocal() as session:
        purged = sessions.purge_expired(session)
        events.log(session, "app_started",
                   detail={"data_dir": str(settings.app_data_dir), "demo_mode": settings.demo_mode,
                           "expired_sessions_purged": purged})

    sys.stdout.write(f"[preflight] storage OK at {settings.app_data_dir}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
