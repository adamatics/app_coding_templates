from sqlmodel import Field

from app.models.base import TimestampMixin


class Department(TimestampMixin, table=True):
    __tablename__ = "departments"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=100, unique=True, index=True)
    code: str = Field(min_length=2, max_length=10, unique=True, index=True)
    description: str | None = Field(default=None, max_length=500)
