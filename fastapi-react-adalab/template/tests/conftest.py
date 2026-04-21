from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.models  # noqa: F401  -- register models with metadata
from app.core.db import get_session
from main import app


@pytest.fixture(name="session")
def session_fixture() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Iterator[TestClient]:
    def _override_get_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture() -> dict[str, str]:
    return {"Authorization": "Bearer demo-token"}


@pytest.fixture(name="department")
def department_fixture(session: Session):
    from app.schemas.department import DepartmentCreate
    from app.services.departments import create_department

    return create_department(session, DepartmentCreate(name="Engineering", code="ENG"))
