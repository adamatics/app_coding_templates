from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.db import get_session
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.services import NotFoundError
from app.services import employees as service

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> list[EmployeeRead]:
    return service.list_employees(session, skip=skip, limit=limit)


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> EmployeeRead:
    try:
        return service.get_employee(session, employee_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> EmployeeRead:
    try:
        return service.create_employee(session, payload)
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Employee with that email already exists or references an invalid department",
        ) from exc


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> EmployeeRead:
    try:
        return service.update_employee(session, employee_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Employee with that email already exists or references an invalid department",
        ) from exc


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> None:
    try:
        service.delete_employee(session, employee_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
