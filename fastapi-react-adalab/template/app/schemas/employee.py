import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class EmployeeBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=200)
    title: str = Field(min_length=1, max_length=100)
    department_id: int
    hire_date: date
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def _email_format(cls, v: str) -> str:
        if not EMAIL_PATTERN.match(v):
            raise ValueError("email must be a valid email address")
        return v


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=200)
    title: str | None = Field(default=None, min_length=1, max_length=100)
    department_id: int | None = None
    hire_date: date | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def _email_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not EMAIL_PATTERN.match(v):
            raise ValueError("email must be a valid email address")
        return v


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
