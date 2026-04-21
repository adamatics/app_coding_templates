import sqlite3
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


@event.listens_for(Engine, "connect")
def _sqlite_enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    Path("./data").mkdir(parents=True, exist_ok=True)
    import app.models  # noqa: F401  -- ensure models register with metadata

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
