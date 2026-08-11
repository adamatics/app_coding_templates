# Chassis vs. seam

The **seam** is the only per-app code. The **chassis** is identical in every app in the
family and is protected from edits.

## The seam (edit these)

| File | What it is |
| --- | --- |
| `exercise/schema.py` | The `Measurement` Pydantic model — one measurement submission |
| `exercise/analysis.py` | Optional `summarize(df) -> dict` for derived statistics |
| `exercise/content.md` | The Home-page instructions (Markdown) |

## The chassis (do NOT edit — the guard blocks these)

`backend/app/**`, the frontend chassis (`frontend/src/App.tsx`, `main.tsx`, `api.ts`,
`metaContext.ts`, `global.d.ts`, `ui.css`, `lib/**`, `components/**`, `pages/**`,
`assets/**`, `vite.config.ts`, `tsconfig.json`, `index.html`, `scripts/**`),
`.adalab/app.json`, `.adalab/project.json`, `.adalab/card.json`, `.vscode/**`,
`Containerfile`, `.claude/settings.json`, `.claude/hooks/**`. The full list is in
`.claude/CLAUDE.md` and enforced by the `chassis_guard` hook.

**Editable with confirmation** (permissions.ask, not blocked): `frontend/src/theme.css`
(CPDSE identity — palette tokens only, never add hex elsewhere),
`.adalab/local_container_demo.json`, and dependency manifests/commands
(`pyproject.toml`, `frontend/package.json`, `pip/npm install`).

## You want X → edit Y

| You want to… | Edit |
| --- | --- |
| Add / remove / rename a measurement field | `exercise/schema.py` |
| Change a field's unit, range, or help text | `exercise/schema.py` (its `Field(...)`) |
| Add a categorical dropdown | `exercise/schema.py` (`Literal["a","b"]`) |
| Add a date field | `exercise/schema.py` (`datetime.date`) |
| Make a field optional | `exercise/schema.py` (`X | None = Field(default=None, ...)`) |
| Add an exercise-specific statistic to Results | `exercise/analysis.py` (`summarize`) |
| Change the Home instructions | `exercise/content.md` |
| Change the entry form layout | **nothing** — the form is generated from the schema |
| Change the results table columns | **nothing** — columns follow the schema field order |
| Add a chart series | **nothing** — numeric fields become chart candidates automatically |
| Change export columns | **nothing** — export columns are the schema fields + cohort/group/submitted/superseded |

## Why it's built this way

Apps in this family must be visually and behaviourally indistinguishable except for their
content, and their data must stay comparable across years. Letting anyone edit the chassis
per app would produce exactly the drift the family exists to prevent. So the chassis is
frozen and everything the exercise needs is expressed once, in the schema.

## If you truly need a chassis change

That is a change to the **template**, not to a stamped app. Make it in the template repo
(where `ALLOW_CHASSIS_EDIT=1` lifts the guard) so every app benefits and none drift.
