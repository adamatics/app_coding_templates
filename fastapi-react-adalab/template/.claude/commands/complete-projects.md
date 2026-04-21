---
description: Complete the Projects feature following the Departments/Employees pattern.
---
Read `TEMPLATE_TODO.md` and `.claude/rules/feature-pattern.md`.

Complete the Projects feature by mirroring `app/api/routes/departments.py`, `app/services/departments.py`, `app/schemas/departments.py` (copy, then change field names to match the Project model). Do the same for the frontend under `frontend/src/routes/projects/`.

Then:
1. Unskip `tests/api/test_projects.py` and implement the tests mirroring `test_departments.py`.
2. Run `/check`.
3. Stop. Do not commit. Report what you did.
