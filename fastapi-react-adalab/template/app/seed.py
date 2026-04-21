from datetime import date

from sqlmodel import Session, select

from app.core.db import engine
from app.models.department import Department
from app.models.employee import Employee

DEPARTMENTS: list[tuple[str, str, str]] = [
    ("Engineering", "ENG", "Builds and maintains the product"),
    ("Sales", "SAL", "Closes business and manages customer accounts"),
    ("Finance", "FIN", "Budgets, payroll, and financial reporting"),
    ("Operations", "OPS", "Keeps the company running day-to-day"),
    ("People", "HR", "Hiring, onboarding, and employee experience"),
]

EMPLOYEES: list[tuple[str, str, str, str, str, date, bool]] = [
    # Engineering (5)
    (
        "Ada",
        "Lovelace",
        "ada.lovelace@example.com",
        "Principal Engineer",
        "ENG",
        date(2021, 2, 1),
        True,
    ),
    (
        "Linus",
        "Torvalds",
        "linus.torvalds@example.com",
        "Staff Engineer",
        "ENG",
        date(2022, 6, 15),
        True,
    ),
    (
        "Grace",
        "Hopper",
        "grace.hopper@example.com",
        "Engineering Manager",
        "ENG",
        date(2020, 11, 3),
        True,
    ),
    (
        "Alan",
        "Turing",
        "alan.turing@example.com",
        "Senior Engineer",
        "ENG",
        date(2023, 5, 20),
        True,
    ),
    (
        "Margaret",
        "Hamilton",
        "margaret.hamilton@example.com",
        "Engineer",
        "ENG",
        date(2024, 1, 10),
        True,
    ),
    # Sales (4)
    (
        "Jordan",
        "Rivera",
        "jordan.rivera@example.com",
        "Account Executive",
        "SAL",
        date(2022, 9, 12),
        True,
    ),
    ("Priya", "Shah", "priya.shah@example.com", "Sales Director", "SAL", date(2021, 4, 2), True),
    (
        "Marcus",
        "Bell",
        "marcus.bell@example.com",
        "Account Executive",
        "SAL",
        date(2023, 7, 18),
        True,
    ),
    (
        "Elena",
        "Rossi",
        "elena.rossi@example.com",
        "Sales Development Rep",
        "SAL",
        date(2024, 2, 5),
        False,
    ),
    # Finance (3)
    ("Robin", "Chen", "robin.chen@example.com", "Finance Manager", "FIN", date(2021, 8, 22), True),
    (
        "Ethan",
        "Park",
        "ethan.park@example.com",
        "Financial Analyst",
        "FIN",
        date(2023, 3, 15),
        True,
    ),
    ("Nadia", "Abadi", "nadia.abadi@example.com", "Controller", "FIN", date(2020, 6, 30), True),
    # Operations (4)
    ("Sam", "Okafor", "sam.okafor@example.com", "Operations Lead", "OPS", date(2022, 1, 17), True),
    ("Mei", "Tan", "mei.tan@example.com", "Operations Analyst", "OPS", date(2023, 11, 4), True),
    (
        "Theo",
        "Nikolaidis",
        "theo.nikolaidis@example.com",
        "IT Operations",
        "OPS",
        date(2021, 10, 8),
        True,
    ),
    (
        "Lila",
        "Brooks",
        "lila.brooks@example.com",
        "Facilities Coordinator",
        "OPS",
        date(2024, 4, 22),
        True,
    ),
    # People (4)
    ("Amira", "Haddad", "amira.haddad@example.com", "People Partner", "HR", date(2022, 3, 9), True),
    ("Kai", "Johansson", "kai.johansson@example.com", "Recruiter", "HR", date(2023, 8, 1), True),
    (
        "Noa",
        "Benjamin",
        "noa.benjamin@example.com",
        "Head of People",
        "HR",
        date(2020, 2, 14),
        True,
    ),
    (
        "Owen",
        "Davis",
        "owen.davis@example.com",
        "Learning & Development",
        "HR",
        date(2024, 6, 11),
        True,
    ),
]


def seed_if_empty() -> None:
    with Session(engine) as session:
        existing = session.exec(select(Department)).first()
        if existing is not None:
            return

        departments_by_code: dict[str, Department] = {}
        for name, code, description in DEPARTMENTS:
            department = Department(name=name, code=code, description=description)
            session.add(department)
            departments_by_code[code] = department
        session.flush()

        for first, last, email, title, code, hire_date, is_active in EMPLOYEES:
            session.add(
                Employee(
                    first_name=first,
                    last_name=last,
                    email=email,
                    title=title,
                    department_id=departments_by_code[code].id,
                    hire_date=hire_date,
                    is_active=is_active,
                )
            )

        session.commit()
