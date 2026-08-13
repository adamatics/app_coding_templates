"""Engine, session, fail-loud storage, startup init (CHASSIS, framework-free — no streamlit).

SQLite in WAL mode so classroom concurrency (§B10: 60 simultaneous sessions) is safe.
Storage is fail-loud (§A3): the shared-volume mount ``DATA_DIR`` is never created by the app;
if it is missing or unwritable the app refuses to start, so student data is never written to
disposable container-local storage. Only the per-app subdirectory inside it is created.
"""
from __future__ import annotations

import textwrap
from collections.abc import Iterator

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import SCHEMA_VERSION, Base, Cohort, Setting

SCHEMA_VERSION_KEY = "_schema_version"


class StorageError(RuntimeError):
    """Raised at startup when DATA_DIR is missing or not writable."""


class SchemaVersionError(RuntimeError):
    """Raised at startup when the database was created by a different chassis schema."""


engine: Engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record) -> None:
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA busy_timeout=30000;")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def require_writable_data_dir() -> None:
    """Verify the shared-volume mount exists and is writable. NEVER create DATA_DIR itself;
    only create this app's subdirectory inside the mounted volume."""
    data_dir = settings.data_dir
    if settings.preview_mode:
        # Storage was relocated to scratch space at import because nothing can be
        # collected without a course password (see core/config.py). Still create the
        # per-app subdirectories so the app runs.
        settings.app_data_dir.mkdir(parents=True, exist_ok=True)
        settings.exports_dir.mkdir(parents=True, exist_ok=True)
        return
    hint = (
        f"Mount the AdaLab Shared Volume at {data_dir} (Fast Mount ON) and chmod it once "
        f"(see README). e.g. locally: docker run -v ./lab-data:{data_dir} ..."
    )
    if not data_dir.exists():
        raise StorageError(textwrap.dedent(f"""
            DATA_DIR does not exist: {data_dir}
            The persistent volume is not mounted. Refusing to start rather than write to
            disposable container-local storage (which is wiped on every redeploy).
            {hint}
        """).strip())
    if not data_dir.is_dir():
        raise StorageError(f"DATA_DIR exists but is not a directory: {data_dir}")
    probe = data_dir / ".write-probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise StorageError(textwrap.dedent(f"""
            DATA_DIR is not writable: {data_dir} ({exc})
            {hint}
        """).strip()) from exc
    # Per-app subdirectory + exports live INSIDE the mounted volume (safe to create).
    settings.app_data_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)


def check_schema_version(session: Session) -> None:
    """Refuse to run against a database written by a different chassis schema.

    ``create_all`` adds missing tables but never alters existing ones, so a changed column
    would otherwise surface as a baffling SQL error halfway through a lab session. Failing at
    startup with instructions is the same stance the app takes on storage. Set
    ``ALLOW_SCHEMA_MISMATCH=1`` to override (after taking a backup).
    """
    import os

    row = session.get(Setting, SCHEMA_VERSION_KEY)
    if row is None:
        session.add(Setting(key=SCHEMA_VERSION_KEY, value=SCHEMA_VERSION))
        session.commit()
        return
    found = row.value
    if found == SCHEMA_VERSION:
        return
    if os.environ.get("ALLOW_SCHEMA_MISMATCH") == "1":
        row.value = SCHEMA_VERSION
        session.commit()
        return
    raise SchemaVersionError(textwrap.dedent(f"""
        Database schema mismatch: the data at {settings.db_path} was written by chassis
        schema version {found}, but this build expects version {SCHEMA_VERSION}.

        New tables are added automatically; a changed table is not. Migrate the data (or
        start a new app directory), then set ALLOW_SCHEMA_MISMATCH=1 for one start to record
        the new version. Take a backup first — Admin -> Export -> Download database.
    """).strip())


def init_db() -> None:
    """Verify storage and schema, create tables, ensure the first open cohort exists."""
    require_writable_data_dir()
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        check_schema_version(session)
        has_cohort = session.execute(select(Cohort.id).limit(1)).first() is not None
        if not has_cohort:
            session.add(Cohort(label=settings.default_year, status="open"))
            session.commit()


def get_session() -> Session:
    return SessionLocal()


def session_scope() -> Iterator[Session]:  # pragma: no cover - convenience
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
