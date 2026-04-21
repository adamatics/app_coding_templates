from datetime import date
from typing import Literal

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlmodel import Field

from app.models.base import TimestampMixin

ProjectStatus = Literal["planning", "active", "on_hold", "completed"]


class Project(TimestampMixin, table=True):
    __tablename__ = "projects"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    status: ProjectStatus = Field(default="planning", sa_type=String(20))
    department_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("departments.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    lead_employee_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("employees.id"),
            nullable=True,
            index=True,
        ),
    )
    start_date: date
    target_date: date | None = None
