"""Engine, session and startup migration (CHASSIS).

SQLite in WAL mode so classroom-scale concurrency (tens of simultaneous writers)
works: WAL lets many readers run while a write is in progress, and ``busy_timeout``
makes concurrent writers wait-and-retry instead of failing with "database is locked".

"Migration" here is intentionally minimal: the schema is chassis-fixed, so
``create_all`` (idempotent) is the whole migration story. The app must run correctly
against an **empty** (but mounted) ``DATA_DIR`` — ``init_db`` creates the file, the tables
and the first open cohort on first start.

Storage is **fail-loud** (Addendum A §A3): the app never creates ``DATA_DIR`` itself. If it
is missing or unwritable the app refuses to start, so student data is never silently written
to disposable container-local storage and lost on the next redeploy.
"""
from __future__ import annotations

import textwrap
from collections.abc import Iterator

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base, Cohort


class StorageError(RuntimeError):
    """Raised at startup when DATA_DIR is missing or not writable."""


def require_writable_data_dir() -> None:
    """Verify DATA_DIR is a mounted, writable directory. NEVER create it.

    Creating it would let a root container silently fall back to container-local storage,
    which looks fine in class and then destroys a year of data at the next redeploy.
    """
    data_dir = settings.data_dir
    mount_hint = (
        f"Mount a persistent volume at {data_dir}, e.g.\n"
        f"    docker run -v ./lab-data:{data_dir} ...\n"
        f"On AdaLab, attach the app's persistent volume so it survives redeploys."
    )
    if not data_dir.exists():
        raise StorageError(textwrap.dedent(f"""
            DATA_DIR does not exist: {data_dir}
            This almost always means the persistent volume is not mounted. Refusing to
            start rather than write to disposable container-local storage.
            {mount_hint}
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
            {mount_hint}
        """).strip()) from exc
    # Only ever create SUB-directories inside the (mounted) DATA_DIR.
    settings.exports_dir.mkdir(parents=True, exist_ok=True)

# check_same_thread=False: the connection is used across FastAPI worker threads.
engine: Engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    # Wait up to 30s for a lock before erroring — carries the concurrency test.
    cursor.execute("PRAGMA busy_timeout=30000;")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Verify storage, then create tables and the first open cohort if the DB is empty."""
    require_writable_data_dir()
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        has_any_cohort = session.execute(select(Cohort.id).limit(1)).first() is not None
        if not has_any_cohort:
            session.add(Cohort(label=settings.default_cohort_label, status="open"))
            session.commit()


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
