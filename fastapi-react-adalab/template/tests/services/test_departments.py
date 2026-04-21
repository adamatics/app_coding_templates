import pytest
from sqlmodel import Session

from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services import NotFoundError
from app.services.departments import (
    create_department,
    delete_department,
    get_department,
    list_departments,
    update_department,
)


def test_list_empty(session: Session) -> None:
    assert list_departments(session) == []


def test_create_and_get(session: Session) -> None:
    created = create_department(
        session,
        DepartmentCreate(name="Engineering", code="ENG", description="Builds stuff"),
    )
    assert created.id is not None
    assert created.name == "Engineering"
    assert created.code == "ENG"

    fetched = get_department(session, created.id)
    assert fetched.id == created.id
    assert fetched.name == "Engineering"


def test_get_missing_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        get_department(session, 9999)


def test_update_partial(session: Session) -> None:
    created = create_department(session, DepartmentCreate(name="Ops", code="OPS"))
    updated = update_department(session, created.id, DepartmentUpdate(description="updated"))
    assert updated.description == "updated"
    assert updated.name == "Ops"
    assert updated.code == "OPS"


def test_update_missing_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        update_department(session, 9999, DepartmentUpdate(description="x"))


def test_delete(session: Session) -> None:
    created = create_department(session, DepartmentCreate(name="Sales", code="SAL"))
    delete_department(session, created.id)
    with pytest.raises(NotFoundError):
        get_department(session, created.id)


def test_delete_missing_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        delete_department(session, 9999)


def test_list_paginated(session: Session) -> None:
    codes = ["AA", "BB", "CC", "DD", "EE"]
    for i, code in enumerate(codes):
        create_department(session, DepartmentCreate(name=f"Dept{i}", code=code))
    assert len(list_departments(session, limit=2)) == 2
    assert len(list_departments(session, skip=2, limit=10)) == 3
