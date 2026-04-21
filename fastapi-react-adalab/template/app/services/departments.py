from sqlmodel import Session, select

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services import NotFoundError


def list_departments(session: Session, skip: int = 0, limit: int = 100) -> list[Department]:
    stmt = select(Department).order_by(Department.id).offset(skip).limit(limit)
    return list(session.exec(stmt).all())


def get_department(session: Session, department_id: int) -> Department:
    department = session.get(Department, department_id)
    if department is None:
        raise NotFoundError(f"Department {department_id} not found")
    return department


def create_department(session: Session, data: DepartmentCreate) -> Department:
    department = Department(**data.model_dump())
    session.add(department)
    session.commit()
    session.refresh(department)
    return department


def update_department(session: Session, department_id: int, data: DepartmentUpdate) -> Department:
    department = get_department(session, department_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(department, key, value)
    session.add(department)
    session.commit()
    session.refresh(department)
    return department


def delete_department(session: Session, department_id: int) -> None:
    department = get_department(session, department_id)
    session.delete(department)
    session.commit()
