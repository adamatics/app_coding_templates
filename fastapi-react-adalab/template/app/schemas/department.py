import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

CODE_PATTERN = re.compile(r"^[A-Z]{2,10}$")


class DepartmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=2, max_length=10)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("code")
    @classmethod
    def _code_uppercase(cls, v: str) -> str:
        if not CODE_PATTERN.match(v):
            raise ValueError("code must be 2-10 uppercase letters")
        return v


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=2, max_length=10)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("code")
    @classmethod
    def _code_uppercase(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not CODE_PATTERN.match(v):
            raise ValueError("code must be 2-10 uppercase letters")
        return v


class DepartmentRead(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
