from datetime import date

import pytest
from sqlmodel import Session

from app.models.department import Department
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services import NotFoundError
from app.services.employees import (
    create_employee,
    delete_employee,
    get_employee,
    list_employees,
    update_employee,
)


def _payload(department: Department, **overrides: object) -> EmployeeCreate:
    base: dict[str, object] = {
        "first_name": "Alice",
        "last_name": "Ng",
        "email": "alice@example.com",
        "title": "Engineer",
        "department_id": department.id,
        "hire_date": date(2024, 1, 15),
        "is_active": True,
    }
    base.update(overrides)
    return EmployeeCreate(**base)


def test_list_empty(session: Session) -> None:
    assert list_employees(session) == []


def test_create_and_get(session: Session, department: Department) -> None:
    created = create_employee(session, _payload(department))
    assert created.id is not None
    assert created.first_name == "Alice"
    assert created.email == "alice@example.com"

    fetched = get_employee(session, created.id)
    assert fetched.id == created.id
    assert fetched.email == "alice@example.com"


def test_get_missing_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        get_employee(session, 9999)


def test_update_partial(session: Session, department: Department) -> None:
    created = create_employee(session, _payload(department))
    updated = update_employee(session, created.id, EmployeeUpdate(title="Senior Engineer"))
    assert updated.title == "Senior Engineer"
    assert updated.first_name == "Alice"
    assert updated.email == "alice@example.com"


def test_update_missing_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        update_employee(session, 9999, EmployeeUpdate(title="X"))


def test_delete(session: Session, department: Department) -> None:
    created = create_employee(session, _payload(department))
    delete_employee(session, created.id)
    with pytest.raises(NotFoundError):
        get_employee(session, created.id)


def test_delete_missing_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        delete_employee(session, 9999)


def test_list_paginated(session: Session, department: Department) -> None:
    for i in range(5):
        create_employee(
            session,
            _payload(
                department,
                first_name=f"User{i}",
                email=f"user{i}@example.com",
            ),
        )
    assert len(list_employees(session, limit=2)) == 2
    assert len(list_employees(session, skip=2, limit=10)) == 3
