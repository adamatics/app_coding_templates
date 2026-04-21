from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Import main AFTER app.core.db so the FastAPI `app` is bound last
# and isn't shadowed by `import app.<submodule>` elsewhere. main.py's
# include_all_routers pulls in every routes module at import time,
# which in turn imports every model, so SQLModel.metadata is fully
# populated by the time the fixtures run create_all().
from app.core.db import get_session  # noqa: E402, I001
from main import app as fastapi_app  # noqa: E402, I001


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

    fastapi_app.dependency_overrides[get_session] = _override_get_session
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture() -> dict[str, str]:
    return {"Authorization": "Bearer demo-token"}


@pytest.fixture(name="department")
def department_fixture(session: Session):
    from app.schemas.department import DepartmentCreate
    from app.services.departments import create_department

    return create_department(session, DepartmentCreate(name="Engineering", code="ENG"))
