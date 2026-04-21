from datetime import date

from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field

from app.models.base import TimestampMixin


class Employee(TimestampMixin, table=True):
    __tablename__ = "employees"

    id: int | None = Field(default=None, primary_key=True)
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=200, unique=True, index=True)
    title: str = Field(min_length=1, max_length=100)
    department_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("departments.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    hire_date: date
    is_active: bool = Field(default=True)
