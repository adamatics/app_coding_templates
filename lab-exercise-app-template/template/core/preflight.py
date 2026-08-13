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

    if settings.storage_blocked:
        # Starts, serves, admits nobody. The container has to come up — the extension's Test
        # step probes it, and a deployer needs to see the reason in the browser — but nothing
        # may be collected onto storage that is about to vanish.
        sys.stderr.write(
            "\n=== NO STORAGE VOLUME — THE APP WILL ADMIT NOBODY ===\n"
            f"DATA_DIR ({settings.configured_data_dir}) is not a mounted, writable volume,\n"
            "and a COURSE_PASSWORD is set, so students could otherwise sign in and submit\n"
            "results that would be lost.\n"
            "The app starts and explains this on screen, but the course gate stays shut.\n\n"
            "To fix, either:\n"
            "  * mount the AdaLab Shared Volume at that path (Fast Mount ON), or\n"
            "  * set STORAGE_MODE=local to use ordinary disk on purpose (not durable).\n\n"
            "This is expected during the extension's Test step, which runs without volumes.\n\n"
        )
    elif settings.preview_mode:
        sys.stderr.write(
            "\n=== PREVIEW MODE — NOT FOR STUDENTS ===\n"
            f"No volume is mounted at the configured DATA_DIR, so the app is running on\n"
            f"scratch space at {settings.data_dir}. Anything written here is LOST when the\n"
            "container stops.\n"
            "No COURSE_PASSWORD is set, so nobody can sign in and nothing can be collected.\n"
            "Mount the Shared Volume before using this with a class.\n\n"
        )

    if settings.local_storage:
        sys.stderr.write(
            "\n=== LOCAL DISK STORAGE — NOT DURABLE ===\n"
            f"STORAGE_MODE=local, so results are written to {settings.data_dir} on this\n"
            "container's own disk instead of an AdaLab Shared Volume.\n"
            "Everything here is ERASED when the container is replaced — which includes\n"
            "every redeploy, every restart of a stopped app, and any resource change.\n"
            "Fine for a laptop, a lab, or a trial. Before a class whose results matter,\n"
            "mount a Shared Volume and unset STORAGE_MODE. If you keep local storage,\n"
            "export from Admin after every session — that is the only copy.\n\n"
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
                           "storage_mode": settings.storage_mode,
                           "storage_is_durable": settings.storage_is_durable,
                           "expired_sessions_purged": purged})

    sys.stdout.write(f"[preflight] storage OK at {settings.app_data_dir}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
