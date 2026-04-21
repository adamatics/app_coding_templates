---
paths: ["app/api/routes/**", "app/services/**", "app/schemas/**", "app/models/**", "tests/**"]
---
# Backend feature pattern

Every entity `X` has these six files, in this order of creation:

1. `app/models/x.py`: SQLModel class. Import it in `app/models/__init__.py`.
2. `app/schemas/x.py`: `XCreate`, `XUpdate`, `XRead`.
3. `app/services/x.py`: module-level functions `list_x(session, skip, limit)`, `get_x(session, id)`, `create_x(session, data)`, `update_x(session, id, data)`, `delete_x(session, id)`. No classes.
4. `app/api/routes/x.py`: `router = APIRouter(prefix="/xs", tags=["xs"])` and 5 endpoints (GET list, GET one, POST, PATCH, DELETE). All depend on `get_current_user` from `deps.py`.
5. `tests/services/test_x.py`: unit tests per service function.
6. `tests/api/test_x.py`: at minimum `test_list_empty`, `test_create_and_get`, `test_create_duplicate_fails`, `test_update`, `test_delete`, `test_unauthenticated_returns_401`.

Model your new entity file-for-file on `app/api/routes/departments.py` etc. Do not invent new patterns.
