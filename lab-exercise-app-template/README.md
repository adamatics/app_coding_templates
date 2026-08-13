# `lab-exercise-app-template`

A [Copier](https://copier.readthedocs.io/) template for **student lab-exercise apps**
for the Center for Pharmaceutical Data Science Education (CPDSE).

Every app stamped from this template serves **one** lab exercise. Student groups record their
measurements; results persist across years for comparison. All apps look and behave
identically (the *chassis*) and differ only in the exercise-specific parts (the *seam*).

> One app = one exercise. The family pattern (many stamped apps) covers everything else.

## What you get

- A **single-process Streamlit app** (Python 3.11), one container, port 8000. No Node, no
  separate API.
- **Architecture that keeps the UI swappable:**

  ```
  core/       framework-free Python — imports streamlit NOWHERE (enforced by a test)
  pages/      thin Streamlit chassis UI
  exercise/   THE SEAM — schema.py, capture.py, analysis.py, content.md
  app.py      entry point, course gate, navigation
  ```

- **CPDSE visual identity** baked in (fixed — no colour/logo questions), applied to both the
  UI and every plot.
- **Identity model**: individual (KUID) → group → hold → year, behind a course-password gate.
  No student accounts, no per-student passwords.
- **Append-only, cohort-based persistence**: corrections supersede, "reset" closes a year.
  SQLite (system of record) + a long-format CSV mirror on a mounted AdaLab Shared Volume,
  with fail-loud startup.
- **"Show the code" panels**: every plot helper returns the figure *and* the standalone
  pandas+plotly code that reproduces it from an exported CSV — a teaching requirement.
- **Four exports**: CSV, Excel, PDF report, HTML report (data + answers + plots).
- **Agent guidance** (`CLAUDE.md`, a `lab-exercise-app` skill, `/new-exercise-field`) and a
  **three-layer guardrail** whose hook actually blocks edits outside the seam.

## Requirements

- [Copier](https://copier.readthedocs.io/) ≥ 9 (`pipx install copier`)
- To build/run a stamped app: Docker or Podman, or a local Python 3.11 toolchain.

## Stamp an app

Copier has no `--directory`/monorepo-subdir flag (that is a cookiecutter feature), so stamp
by pointing Copier at this template's subdirectory of a clone:

```bash
git clone git@github.com:adamatics/app_coding_templates.git
copier copy app_coding_templates/lab-exercise-app-template ./my-exercise --trust
```

The app is generated directly in `./my-exercise/`. Then:

```bash
cd my-exercise
podman build -t my-exercise .
mkdir -p ./lab-data
podman run -p 8000:8000 -v ./lab-data:/asv-mnt/lab-data \
  -e COURSE_PASSWORD=lab2026 -e ADMIN_PASSWORD=change-me my-exercise
# open http://localhost:8000/my-exercise/
```

Note the URL prefix: Streamlit is run with `--server.baseUrlPath`, and `.adalab/app.json` sets
`stripped_prefix: false`, because Streamlit needs the prefix on incoming requests (verified —
see `HANDOVER.md` §B1).

## Customising the exercise (the seam)

Inside a stamped app you edit **only these four files**:

```
exercise/schema.py     the Measurement model — drives storage, CSV and all exports
exercise/capture.py    the Streamlit input form
exercise/analysis.py   the plots, built with core.plots (each gets "Show the code")
exercise/content.md    instructions + the analysis questions
```

You never touch the chassis; a `chassis_guard` hook enforces it.

### Template-maintainer escape hatch

If **you** are editing the template's chassis (this repo), set `ALLOW_CHASSIS_EDIT=1` to
disable the guard. Documented only here, not in the stamped app.

## Testing a stamped app

```bash
DATA_DIR=$(mktemp -d) python -m pytest -q      # 122 tests
```

The suite includes the three load-bearing checks: `core/` imports with **no streamlit
installed**, every plot's "Show the code" **runs standalone** against an exported CSV, and
**60 simultaneous sessions** submit without error or cross-session leakage.

## Template layout

```
lab-exercise-app-template/
├── copier.yml        # the questions + _subdirectory: template
├── SPEC.md           # authoritative spec for working on the template itself
├── README.md         # this file
├── DECISIONS.md      # decisions taken where the specs were silent/ambiguous
├── HANDOVER.md       # build report across the base spec + Addendum A + Addendum B
└── template/         # the stamped app contents (rendered into the output path)
```

## Design principles

1. **Chassis vs. seam**, enforced not just documented. The seam is Python only, so CPDSE
   scientists working with coding agents can own it for years.
2. **`core/` is framework-free** — the seed of the shared library later apps will depend on.
3. **Data durability**: append-only, close-never-delete, fail-loud storage, stable export
   columns across years.
4. **One visual identity**: CPDSE colours live only in `core/theme.py`.

See `SPEC.md` for how to work on the template, and `Lab_Exercise_App_Template_Spec.md`,
`..._Addendum_A.md`, `..._Addendum_B.md` for the full specification (later documents win).
Note: unlike the monorepo's per-prospect templates, this template's CPDSE identity is
**fixed** (no branding questions) — a deliberate requirement of the CPDSE spec, with the
artwork in `template/assets/`. See the divergences section of `SPEC.md`.
