from sqlmodel import Session, select

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services import NotFoundError


def list_employees(session: Session, skip: int = 0, limit: int = 100) -> list[Employee]:
    stmt = select(Employee).order_by(Employee.id).offset(skip).limit(limit)
    return list(session.exec(stmt).all())


def get_employee(session: Session, employee_id: int) -> Employee:
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise NotFoundError(f"Employee {employee_id} not found")
    return employee


def create_employee(session: Session, data: EmployeeCreate) -> Employee:
    employee = Employee(**data.model_dump())
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def update_employee(session: Session, employee_id: int, data: EmployeeUpdate) -> Employee:
    employee = get_employee(session, employee_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(employee, key, value)
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def delete_employee(session: Session, employee_id: int) -> None:
    employee = get_employee(session, employee_id)
    session.delete(employee)
    session.commit()
