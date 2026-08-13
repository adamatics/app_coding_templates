# SPEC — `lab-exercise-app-template`

Authoritative spec for working on **this template's source** (per REPO_SPEC §10). Full
requirements live in `Lab_Exercise_App_Template_Spec.md` (base),
`..._Addendum_A.md` (AdaLab conventions + persistence) and `..._Addendum_B.md` (the Streamlit
switch); **later documents win on conflict**. `DECISIONS.md` records ambiguous calls;
`HANDOVER.md` is the build report and acceptance results.

## Purpose

Stamp out CPDSE (Center for Pharmaceutical Data Science Education) student lab-exercise apps.
Each app serves **one** lab exercise: student groups record measurements, compare against the
class and previous years, and export a report they keep. Apps are a family — identical
chassis, per-course seam.

## Stack (fixed)

Python **3.11**, **Streamlit** (single process, single container, **port 8000**), pandas,
plotly, lmfit, SQLAlchemy 2, Pydantic v2, SQLite (WAL), reportlab (PDF), openpyxl (Excel).
No Node, no separate API, no database server, no Alembic.

## Architecture (non-negotiable, Addendum §B1)

```
core/       framework-free Python — imports streamlit NOWHERE (a test enforces it)
pages/      thin Streamlit chassis UI
exercise/   THE SEAM — schema.py, capture.py, analysis.py, content.md
assets/     brand artwork (CPDSE logo)
app.py      entry point, course gate, navigation
```

`core/` is the seed of the shared library later apps will depend on, which is why the
no-streamlit rule is tested three ways. `exercise/schema.py` is imported by `core/`, so it
must stay framework-free too.

## AdaLab constraints (§A1, §A3, §B1)

- `Containerfile` (never `Dockerfile`); single stage on `python:3.11-slim`.
- `.adalab/` = `project.json`, `app.json`, `local_container_demo.json` (`uid: 1`, ports 8000,
  `volume_mounts: []`), plus `.vscode/settings.json`.
- **`stripped_prefix: false`** + `--server.baseUrlPath` — Streamlit needs the URL prefix on
  incoming requests. This is a deliberate divergence from Addendum A, found by the §B1
  deployment check; see HANDOVER §1.
- **`access_level: "public"`** — students have no AdaLab accounts; the course password is the gate.
- **Fail-loud storage:** the app never creates `DATA_DIR`; `core/preflight.py` runs *before*
  Streamlit and exits non-zero if the volume is missing or unwritable.
- Single replica (WAL). ASV **Fast Mount** required. `lost+found` / `.AVI_SUCCESS` filtered.
  Non-SQLite volume writes are atomic.

## The seam (the only per-app code)

| File | What it is |
| --- | --- |
| `exercise/schema.py` | The `Measurement` model. Framework-free. Drives storage, CSV and every export. |
| `exercise/capture.py` | The **data entry page**: `render_form(defaults)` → payload dict; optional `render_intro()`. |
| `exercise/analysis.py` | The **analysis page**: `build_plots(own_df, compare_df, source)` using `core.plots`. |
| `exercise/content.md` | Instructions + the `## Analysis questions` list (rendered with answer fields). |

Both page files ship as **annotated teaching templates** — a teacher (usually with an agent)
rewrites them per course, so the file itself explains its purpose and contract.

## Identity and data model

**Individual (KUID) → Group (carries hold) → Hold → Year**, behind a course-password gate
(`COURSE_ID`/`COURSE_PASSWORD`). No student accounts, no per-student passwords. Durable
browser sessions via an opaque token in the URL (`session_token` table).

Tables: `cohort` (year, one open) · `group` · `member` (unique KUID per cohort) · `result`
(append-only, `superseded_by`, `deleted_at`) · `answer` · `setting` · `document` ·
`session_token` · `event`.

Rules: **append-only** (corrections supersede); **reset = close the year, never delete**;
writes to a closed year are 409; hard delete is admin-only, one row, audited. Export columns
are stable across years. `SCHEMA_VERSION` guards chassis schema changes at startup.

## Logging

`core/events.py` records registrations, submissions, overwrites (old + new values), exports,
admin actions and errors to three sinks: the `event` table (Admin → Log), stdout, and
`events.jsonl` on the volume. Logging can never break the app. stdout is pseudonymous unless
`LOG_PII=true`.

## Protected zones (three-layer guardrail, §B9)

`core/**`, `pages/**`, `app.py`, `assets/**`, `.adalab/{app,project,card}.json`, `.vscode/**`,
`Containerfile`, lockfiles, `.claude/settings.json`, `.claude/hooks/**` — named identically in
`permissions.deny`, the hook's `PROTECTED` list, and `CLAUDE.md`. **Ask** tier:
`.adalab/local_container_demo.json`, `pyproject.toml`, `.streamlit/config.toml`, dependency
commands. Only `exercise/**` is always writable.

## Copier questions

`project_name`, `project_slug`, `exercise_title`, `course_code`, `app_description`,
`host_institution`, `contact_email`, `default_cohort_label`. **No colour or logo questions.**

## Definition of Done

Base spec §15, Addendum A §A6, Addendum B §B10 — results in `HANDOVER.md`. The three
load-bearing checks: `core/` imports with no Streamlit installed; every plot's "Show the code"
runs standalone against an exported CSV; 60 simultaneous sessions submit with no errors and no
cross-session leakage. **122 tests** at time of writing.

## Testing

```bash
copier copy app_coding_templates/lab-exercise-app-template /tmp/test-1 --trust
cd /tmp/test-1 && DATA_DIR=$(mktemp -d) python -m pytest -q
podman build -t test-1 . && mkdir -p ./lab-data
podman run -p 8000:8000 -v ./lab-data:/asv-mnt/lab-data -e COURSE_PASSWORD=x -e ADMIN_PASSWORD=y test-1
```

## Divergences from REPO_SPEC (intentional — for maintainer review)

- **Branding is FIXED, not per-prospect.** The CPDSE spec (§4, §13) forbids colour/logo
  questions; the identity lives in `core/theme.py` with artwork in `template/assets/`. There is
  no `logo.svg`/`tokens.css` branding contract; `_skip_if_exists` protects `core/theme.py` and
  `assets/*` instead.
- **Domain question names** (`project_name`/`exercise_title`/…) rather than `prospect_name`;
  `app_description` is present as REPO_SPEC requires.
- **Guardrail hook is `chassis_guard.py`** (not `protect_paths.py`); **no subagents** yet;
  rules are in `.claude/rules/` and path-scoped via frontmatter. Stamp-time logic uses copier
  `_tasks` rather than `hooks/post_gen.py`.
- **Stack is Streamlit, not FastAPI + React** — Addendum B, so CPDSE scientists can own the
  seam in Python.
- **Stamping form:** REPO_SPEC documents `copier copy … --directory <template>`, but
  `--directory` is a *cookiecutter* flag; Copier ≥ 9 has no such option. The working form is to
  clone and point Copier at the subdirectory. A maintainer may want a root `copier.yml` or a
  wrapper to restore a one-liner.
