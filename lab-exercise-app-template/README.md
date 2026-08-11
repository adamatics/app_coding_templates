# `lab-exercise-app-template`

A [Copier](https://copier.readthedocs.io/) template for **student lab-exercise apps**
for the Center for Pharmaceutical Data Science Education (CPDSE).

Every app stamped from this template serves **one** lab exercise. Student groups record
their measurements; results persist across years for statistical comparison. All apps look
and behave identically (the *chassis*) and differ only in the exercise-specific parts (the
*seam*): the measurement schema, the form derived from it, and the analysis/instructions.

> One app = one exercise. The family pattern (many stamped apps) covers everything else.

## What you get

- **FastAPI + SQLite (WAL)** backend, **React 18 + Vite + TypeScript** frontend, built to
  static files and served by the *same* FastAPI process. One container, one process, one port.
- **CPDSE visual identity** baked in (fixed — no colour/logo questions).
- **Append-only, cohort-based persistence**: corrections supersede, "reset" closes a cohort
  instead of deleting. No code path destroys historical data.
- **Admin area** (single password from env), **CSV/Parquet export**, **demo data**.
- **Agent guidance** (`CLAUDE.md`, a `lab-exercise-app` skill, a `/new-exercise-field`
  command) and a **chassis-guard hook** that blocks edits outside the exercise seam.

## Requirements

- [Copier](https://copier.readthedocs.io/) ≥ 9 (`pipx install copier` or `pip install copier`)
- To build/run a stamped app: Docker or Podman, or a local Python 3.11 + Node 18+ toolchain.

## Stamp an app

Copier has no `--directory`/monorepo-subdir flag (that is a cookiecutter feature), so stamp
by pointing Copier at this template's subdirectory of a clone:

```bash
git clone git@github.com:adamatics/app_coding_templates.git
copier copy app_coding_templates/lab-exercise-app-template ./my-exercise --trust
```

You will be asked a short list of questions (spec §4). The app is generated directly in
`./my-exercise/`. Then (a writable volume MUST be mounted at `/asv-mnt/lab-data`):

```bash
cd my-exercise
podman build -t my-exercise .          # or: docker build -f Containerfile -t my-exercise .
podman run -p 8000:8000 -v ./lab-data:/asv-mnt/lab-data -e ADMIN_PASSWORD=change-me my-exercise
# open http://localhost:8000
```

## Customising the exercise (the seam)

Inside a stamped app you edit **only three files**:

```
exercise/schema.py     # the Pydantic Measurement model — the single source of truth
exercise/analysis.py   # optional exercise-specific derived statistics
exercise/content.md    # the Home-page instructions
```

The results form, the results table, the chart candidates and the export columns **all
follow from `schema.py` automatically**. You never touch the chassis. A `chassis_guard`
hook enforces this by blocking writes to chassis files.

### Template-maintainer escape hatch

The chassis guard is meant to protect app authors from themselves. If **you** are editing
the template's chassis (this repo), set `ALLOW_CHASSIS_EDIT=1` in your environment to disable
the guard. This is intentionally documented only here, in the template README — not in the
stamped app — so app authors don't discover an easy way around the seam boundary.

## Template layout

```
lab-exercise-app-template/
├── copier.yml        # the questions (spec §4) + _subdirectory: template
├── SPEC.md           # authoritative spec for building the template itself
├── README.md         # this file
├── DECISIONS.md      # decisions taken where the spec was silent/ambiguous
├── HANDOVER.md       # build report against the spec + addendum
└── template/         # the stamped app contents (rendered into the output path)
```

## Design principles (from the spec)

1. **Chassis vs. seam.** The chassis is identical in every app and never edited per-app.
   The seam (`exercise/`) is the only customization surface. This is enforced, not just
   documented.
2. **Data durability.** Append-only results with supersede semantics; cohort *close*, never
   delete; closed cohorts stay fully queryable and exportable; export columns are stable
   across years so cohorts concatenate directly.
3. **One visual identity.** CPDSE branding is fixed in the chassis. No raw hex outside
   `frontend/src/theme.css`; only the six approved fill/ink pairs; Verdana with declared
   fallbacks.

See `SPEC.md` for the full specification (and `DECISIONS.md` / `HANDOVER.md` for the build
record). Note: unlike the monorepo's per-prospect templates, this template's CPDSE identity
is **fixed** (no branding questions, no `logo.svg`/`tokens.css` swap) — that is a deliberate
requirement of the CPDSE spec, called out in `SPEC.md`.
