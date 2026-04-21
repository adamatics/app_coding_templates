from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.db import get_session
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.services import NotFoundError
from app.services import departments as service

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentRead])
def list_departments(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> list[DepartmentRead]:
    return service.list_departments(session, skip=skip, limit=limit)


@router.get("/{department_id}", response_model=DepartmentRead)
def get_department(
    department_id: int,
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> DepartmentRead:
    try:
        return service.get_department(session, department_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> DepartmentRead:
    try:
        return service.create_department(session, payload)
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Department with that name or code already exists",
        ) from exc


@router.patch("/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> DepartmentRead:
    try:
        return service.update_department(session, department_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Department with that name or code already exists",
        ) from exc


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    session: Session = Depends(get_session),
    _user: str = Depends(get_current_user),
) -> None:
    try:
        service.delete_department(session, department_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
