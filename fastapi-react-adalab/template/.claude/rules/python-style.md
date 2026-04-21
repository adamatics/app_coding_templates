---
paths: ["**/*.py"]
---
# Python style

- Python 3.11 syntax. Use `str | None`, not `Optional[str]`.
- Type hints on every function parameter and return.
- SQLModel for all DB models. Never raw SQL.
- Pydantic v2 for schemas. Separate `Create`, `Update`, `Read`.
- Services return domain objects or raise exceptions. Routes catch and translate to HTTPException.
- Tests use `pytest`, not `unittest`. Use fixtures from `conftest.py`.
