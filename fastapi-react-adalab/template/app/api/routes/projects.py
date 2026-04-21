"""Project routes — STUB.

TODO: implement an APIRouter mirroring app/api/routes/departments.py
(or app/api/routes/employees.py). Five endpoints (GET list, GET one,
POST, PATCH, DELETE) all behind Depends(get_current_user). Translate
NotFoundError -> 404 and IntegrityError -> 409.

The aggregator in app/api/main.py auto-discovers any module here
that defines a `router` attribute, so once you add
`router = APIRouter(prefix="/projects", tags=["projects"])` the
endpoints register automatically. No edits to app/api/main.py.

See TEMPLATE_TODO.md step 3 and .claude/rules/feature-pattern.md.
"""
