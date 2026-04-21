import csv
import io

from openpyxl import Workbook
from sqlmodel import Session, select

from app.models.department import Department
from app.models.employee import Employee


def analyze_csv_bytes(filename: str, content: bytes) -> dict:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return {
            "filename": filename,
            "rows": 0,
            "columns": 0,
            "headers": [],
            "preview": [],
        }
    headers = rows[0]
    data_rows = rows[1:]
    return {
        "filename": filename,
        "rows": len(data_rows),
        "columns": len(headers),
        "headers": headers,
        "preview": data_rows[:5],
    }


def _employees_with_department(
    session: Session,
) -> list[tuple[Employee, Department | None]]:
    employees = list(session.exec(select(Employee).order_by(Employee.id)).all())
    departments = {d.id: d for d in session.exec(select(Department)).all() if d.id is not None}
    return [(e, departments.get(e.department_id)) for e in employees]


_HEADERS = [
    "id",
    "first_name",
    "last_name",
    "email",
    "title",
    "department_code",
    "department_name",
    "hire_date",
    "is_active",
    "created_at",
]


def export_employees_csv(session: Session) -> bytes:
    rows = _employees_with_department(session)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_HEADERS)
    for e, d in rows:
        writer.writerow(
            [
                e.id,
                e.first_name,
                e.last_name,
                e.email,
                e.title,
                d.code if d else "",
                d.name if d else "",
                e.hire_date.isoformat(),
                "yes" if e.is_active else "no",
                e.created_at.isoformat() if e.created_at else "",
            ]
        )
    return buf.getvalue().encode("utf-8-sig")


def export_employees_xlsx(session: Session) -> bytes:
    rows = _employees_with_department(session)
    wb = Workbook()
    ws = wb.active
    ws.title = "Employees"
    ws.append(_HEADERS)
    for e, d in rows:
        ws.append(
            [
                e.id,
                e.first_name,
                e.last_name,
                e.email,
                e.title,
                d.code if d else "",
                d.name if d else "",
                e.hire_date.isoformat(),
                bool(e.is_active),
                e.created_at.isoformat() if e.created_at else "",
            ]
        )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
