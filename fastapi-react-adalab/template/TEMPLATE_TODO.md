# Template TODO

Two lists live in this repo:

- **`FEATURES_TODO.md`** — the list of features *you* want to build. This is your input to Claude Code. Start there.
- **This file (`TEMPLATE_TODO.md`)** — template-level scaffolding work. Only the Projects feature is listed below. Delete this file once Projects is complete and you no longer need a reference for the feature-pattern.

See `DEVELOPER_GUIDE.md` for the first-run tour.

## Projects feature (incomplete)

The `Project` SQLModel is defined; routes, service, schemas, UI, and tests are stubs. To complete:

1. Create `app/schemas/project.py` with `ProjectCreate`, `ProjectUpdate`, `ProjectRead`.
2. Implement `app/services/projects.py`, mirroring `app/services/departments.py`.
3. Implement `app/api/routes/projects.py`, mirroring `app/api/routes/departments.py`. The aggregator will pick it up automatically.
4. Add `frontend/src/types/project.ts` and `frontend/src/api/projects.ts`.
5. Implement `frontend/src/routes/projects/index.tsx`, `$id.tsx`, `new.tsx`.
6. Unskip and implement `tests/api/test_projects.py`.
7. Run `uv run pytest -q && cd frontend && pnpm run test`.
8. Rebuild via AdaLab Test → Build → Deploy to see it live.

Do not create migrations. Schema changes happen via `SQLModel.metadata.create_all()` at startup.
