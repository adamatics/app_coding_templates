from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

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
