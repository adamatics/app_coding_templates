# SPEC — `lab-exercise-app-template`

Authoritative spec for working on **this template's source** (per REPO_SPEC §10). The full
requirements are in `Lab_Exercise_App_Template_Spec.md` (base) and
`Lab_Exercise_App_Template_Addendum_A.md` (AdaLab conventions + persistence; wins on
conflict). `DECISIONS.md` records ambiguous calls; `HANDOVER.md` is the build report and
acceptance results.

## Purpose

Stamp out CPDSE (Center for Pharmaceutical Data Science Education) student lab-exercise apps.
Each stamped app serves **one** lab exercise: student groups record measurements, and results
persist across cohorts (years) for statistical comparison. Apps are visually and behaviourally
identical (the **chassis**) and differ only in the **exercise seam**.

## Stack (fixed)

- Backend: Python **3.11**, FastAPI, uvicorn, SQLite (WAL), SQLAlchemy 2.x, Pydantic v2.
- Frontend: React 18 + Vite + TypeScript, built to static and served by the **same** FastAPI
  process. One container, one process, **port 8000**.
- Persistence: single SQLite file under `DATA_DIR` (default `/asv-mnt/lab-data`), an AdaLab
  Shared Volume. No database server. No Alembic (`create_all` at startup).

## AdaLab constraints (Addendum §A1, §A3)

- `Containerfile` (never `Dockerfile`); multi-stage (Node 20 build → `python:3.11-slim`).
- `.adalab/` = `project.json`, `app.json`, `local_container_demo.json` (`uid: 1`,
  `stripped_prefix: true`, `port`/`test_serving_port` 8000, `volume_mounts: []`), plus
  `.vscode/settings.json` = `{"adalab.workingMode": "appBuilder"}`.
- **Base path resolved at runtime in the frontend** (`frontend/src/lib/basepath.ts` from
  `window.location.pathname`); AdaLab strips the `/apps/<slug>/` prefix, so the backend serves
  at root. No `BASE_PATH` env var.
- **Fail-loud storage:** the app never creates `DATA_DIR`; a missing/unwritable volume stops
  startup with the path + mount fix. Never silently fall back to container-local storage.
- Single-replica (WAL); ASV **Fast Mount** required; `lost+found` and `.AVI_SUCCESS` filtered
  wherever the app enumerates volume contents; non-SQLite volume writes are atomic
  (temp-then-`replace`).

## The seam (the only per-app code)

```
exercise/schema.py     one Pydantic model `Measurement`  → form, table, chart, export all follow
exercise/analysis.py   optional summarize(df) -> dict
exercise/content.md    Home-page instructions
```

Changing an exercise = editing these three files only. The chassis derives the entry form
(`SchemaForm`), the results table, chart candidates (numeric fields) and the export columns
from the JSON Schema of `Measurement`.

## Data model (chassis; durability is load-bearing)

`cohort` (one `open` at a time) · `group` (unique per cohort, case-insensitive) · `member` ·
`result` (JSON `payload`, `superseded_by`, `deleted_at`) · `audit`. Rules: **append-only**
(students never edit/delete; corrections *supersede*); **reset = close a cohort + open a new
one**, never delete; writes to a closed cohort are 409; hard-delete is admin-only, single-row,
audited. Export columns = schema fields + `cohort, group, submitted_at, superseded`, stable
across years.

## Protected zones (three-layer guardrail — Addendum §A4)

The seam `exercise/**` is the only always-writable zone. Chassis is protected by a single
set named identically in three layers (`.claude/settings.json` `permissions.deny`, the
`chassis_guard.py` `PROTECTED` list, and `.claude/CLAUDE.md`): `backend/app/**`, the frontend
chassis (`App.tsx`, `main.tsx`, `api.ts`, `metaContext.ts`, `global.d.ts`, `ui.css`, `lib/**`,
`components/**`, `pages/**`, `assets/**`, `vite.config.ts`, `tsconfig.json`, `index.html`,
`scripts/**`), `.adalab/{app,project,card}.json`, `.vscode/**`, `Containerfile`,
`.claude/settings.json`, `.claude/hooks/**`. **Ask** (editable with confirmation):
`frontend/src/theme.css`, `.adalab/local_container_demo.json`, dependency manifests/commands.
The hook (real enforcement) exits 2 to block edits and dangerous Bash.

## `.claude/` (stamped into every app)

`CLAUDE.md` (chassis/seam intent), `settings.json` (deny/ask + PreToolUse `chassis_guard.py`,
PostToolUse `format.py` (ruff/prettier), SessionStart `session_start.py`), `hooks/`,
`rules/*.md`, the `lab-exercise-app` skill (+ `chassis-vs-seam`, `schema-cookbook`,
`data-model` references), and the `/new-exercise-field` command.

## Copier questions

`project_name`, `project_slug` (derived), `exercise_title`, `course_code`, `host_institution`
(SDU|UCPH|CPDSE, footer only), `contact_email`, `default_cohort_label`, `app_description`.
**No colour/logo questions** — the CPDSE identity is fixed (spec §4, §13).

## Definition of Done

Base spec §15 (1–10) and Addendum §A6 (11–17). Summary of current status is in `HANDOVER.md`:
all locally verifiable items pass (41 pytest, container build on 3.11, fail-loud, restart +
new-image-tag redeploy persistence, three-layer guardrail consistency, brand no-hex check);
items needing a live AdaLab tenant (the `/apps/<slug>/` deploy, card deploy, ASV runbook) are
marked as such.

## Build order

Data layer + tests → public API → admin auth/API → frontend shell + theme + Groups/EnterResults
→ Results/compare → export → demo seed → Containerfile + basepath → agent guidance + hook →
worked example seam → acceptance run. (Base spec §16.)

## Divergences from REPO_SPEC (intentional — for maintainer review)

This template implements the CPDSE spec, which differs from the monorepo's per-prospect demo
conventions. Flagged so a maintainer can decide whether to reconcile:

- **Branding is FIXED, not per-prospect.** The CPDSE spec (§4, §13) forbids colour/logo
  questions and fixes the identity in `frontend/src/theme.css`. There is no
  `frontend/public/logo.svg` / `frontend/src/styles/tokens.css` branding contract and no
  `_skip_if_exists` on those. `_skip_if_exists` protects `theme.css` instead.
- **Question names are domain-specific** (`project_name`/`exercise_title`/… rather than
  `prospect_name`); `app_description` is present as REPO_SPEC requires.
- **Guardrail hook is `chassis_guard.py`** (not `protect_paths.py`), and there are **no
  `business-logic-implementer` / `security-reviewer` subagents** yet; rules are in
  `.claude/rules/` but not path-scoped via frontmatter. Stamp-time logic uses copier `_tasks`
  (chmod + `git init`) rather than `hooks/post_gen.py`.
- **Data model is the exercise domain** (cohorts/groups/members/results), not
  Departments/Employees/Projects.
- **Stamping form.** `REPO_SPEC.md` documents `copier copy ... --directory <template>`, but
  `--directory` is a *cookiecutter* flag — Copier ≥ 9 has no such option and no remote
  monorepo-subdir selection. The working form is to clone the repo and point Copier at the
  template subdirectory (`copier copy app_coding_templates/lab-exercise-app-template <out>
  --trust`). A maintainer may want a root `copier.yml` or a wrapper to restore a one-liner;
  flagged rather than silently diverged.
