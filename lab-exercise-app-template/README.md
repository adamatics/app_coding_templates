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
- **Exports**: CSV, Excel, PDF and HTML reports (data + answers + plots), plus an answers
  CSV, a full workbook and a SQLite backup for the teacher.
- **Event log** of registrations, submissions, corrections, exports and errors — to the
  database, stdout and a durable file on the volume.
- **Course documents**: the teacher uploads the øvelsesvejledning; students download it in-app.
- **Agent guidance** (`CLAUDE.md`, a `lab-exercise-app` skill, `/new-exercise-field`) and a
  **three-layer guardrail** whose hook actually blocks edits outside the seam.

## Requirements

- [Copier](https://copier.readthedocs.io/) ≥ 9 (`pipx install copier`)
- To build/run a stamped app: Docker or Podman, or a local Python 3.11 toolchain.

## Stamp an app

> **Working in an AdaLab lab?** Follow **[GETTING-STARTED-ADALAB.md](GETTING-STARTED-ADALAB.md)**
> instead — a step-by-step walkthrough for the lab terminal, from installing Copier to
> deploying, with a check after every step. No GitHub account needed; the repo is public.

```bash
copier copy gh:cpdse/lab-exercise-app-template ./exercises --trust
```

The app is generated at `./exercises/<project_slug>/`. Then:

```bash
cd exercises/<project_slug>
podman build -t <project_slug> .
mkdir -p ./lab-data
podman run -p 8000:8000 -v ./lab-data:/asv-mnt/lab-data \
  -e COURSE_PASSWORD=lab2026 -e ADMIN_PASSWORD=change-me <project_slug>
# open http://localhost:8000/
```

Note the URL prefix: the app serves at the **container root** and `.adalab/app.json` keeps
AdaLab's default `stripped_prefix: true`. Streamlit emits relative asset URLs, so everything
resolves correctly under `/apps/<slug>/` once the proxy strips the prefix — and the container
still answers `/`, which the extension's Test step requires. See `HANDOVER.md` §B1.

## Designing the UI: the live preview loop

`copier → build → test` is the **release gate**, not the edit loop. Running it after every
layout tweak costs minutes and still cannot show you how a page *looks* — the container proves
the app starts, and the tests prove the widgets exist, but neither shows spacing, colour, or a
chart crowding its caption.

For design work, run the template directly:

```bash
python3 scripts/dev.py
```

Then edit `template/{{project_slug}}/ui/**`, `exercise/**` or `core/theme.py` and **save** —
the page reruns in the browser. Seconds, not minutes, and you are editing the template itself
rather than a copy you would have to port changes back from.

**How it works.** Copier renders only files ending in `.jinja`. Exactly one Python file in the
whole template is templated (`core/config.py.jinja`) and nothing under `ui/` is — so `dev.py`
stamps once into `.devapp/`, then replaces every plain file with a **symlink back to the
template**. Streamlit resolves the symlink, watches the real file, and reruns on save.

| | |
| --- | --- |
| Sign in with | course password `dev`, admin password `dev` |
| Demo data | seeded by default, so charts and tables have content — empty screens hide most layout problems |
| `--empty` | start with no data, to inspect the first-run state deliberately |
| `--port N` | default 8501 |
| `--rebuild` | re-render the `.jinja` files (done automatically when one changes) |

`.devapp/` and `.devdata/` are working directories, both git-ignored. Delete `.devdata/` to
start a fresh cohort.

**What it does not cover.** The dev loop uses your local Python, not the container, and serves
at the root without a proxy. So before you commit, still run the gate — the tests and a
container build — which is what catches dependency, prefix and packaging problems:

```bash
copier copy . /tmp/check --defaults --trust -d project_slug=check-lab && cd /tmp/check/check-lab && python3 -m pytest -q
```

## Before an app can run: the Shared Volume

> **Just trying it out?** Set `STORAGE_MODE=local` and the app writes to an ordinary
> directory instead, creating it if needed — no volume, no mount, no `chmod`. Data then lives
> on the container's own disk and is **erased by every redeploy or restart**, so the app says
> so on every screen and pushes you to export. See *Local disk instead of a volume* below.

Stamping and deploying is not enough — **every app needs an AdaLab Shared Volume (ASV), and
the volume is created separately from the app.** This is the step that is not part of the VS
Code extension and the one that most often blocks a first deployment.

The app **refuses to start without a writable volume**, deliberately: writing to container-local
storage would work all semester and then lose a year of student results at the next redeploy.

Four steps, in order:

1. **Create the volume** on the AdaLab **Volumes** page — name, description, **size in GB
   (fixed at creation)**, then access control (**View / Mount / Edit**, hierarchical). *At some
   institutions only an admin can do this — find out early.*
2. **Fix the filesystem permissions.** A new volume has ACL access but no filesystem
   permissions: the mount succeeds and every write still fails with `PermissionError`. Once per
   volume, from a lab terminal:
   ```bash
   cd ~/asv-mnt
   sudo chown root:$NB_GROUP <Volume_Name>
   sudo chmod 775 <Volume_Name>
   ```
   `<Volume_Name>` is the volume's name **with spaces replaced by underscores**
   (`CPDSE Lab Data` → `CPDSE_Lab_Data`) — `ls ~/asv-mnt` to check. Becomes implicit in
   AdaLab v1.6.
3. **Mount it into the app** in the App Deployment wizard, on the **primary container**:
   mount path `lab-data` (the part *after* `/asv-mnt/`, no leading or trailing slash),
   **Read only off**, **Fast Mount on**. The mount path must match `DATA_DIR` — a test in the
   stamped app checks they agree.
4. **Verify** — start the app, submit a result, redeploy, confirm it survived.

**Fast Mount is required, not optional:** ASVs are network filesystems, and SQLite over a
network mount is slow and can corrupt under load. One Fast Mount per app.

One ASV can be mounted into **several course apps at once** (each writes to its own
subdirectory), which is how a student's history stays reachable across a course.

The stamped app carries the full runbook in its own README, and agents working in the app get
it from `.claude/skills/lab-exercise-app/references/adalab-deployment.md`.

### Local disk instead of a volume

`STORAGE_MODE=local` writes results to `DATA_DIR` as an ordinary directory, creating it if it
does not exist:

```bash
podman run -p 8000:8000 -e STORAGE_MODE=local \
  -e COURSE_PASSWORD=lab2026 -e ADMIN_PASSWORD=change-me <project_slug>
```

In AdaLab, set `STORAGE_MODE=local` in the deploy wizard's environment variables and leave
**Volume mounts** empty.

**What you give up.** Container-local data is erased whenever the container is replaced — every
redeploy, every restart of a stopped app, every resource change. So it is right for a laptop, a
lab, a demo, or a first trial before anyone has provisioned a volume, and wrong for a class
whose results matter unless you export after every session.

The app does not let this pass quietly:

- a standing notice on **every screen**, including the sign-in page
- a warning block at startup in the container log
- a notice on **Admin → Export** saying the download is the only lasting copy
- `storage_mode` and `storage_is_durable` recorded in the `app_started` event

**It is never reached by accident.** Without `STORAGE_MODE=local`, a missing volume still
aborts startup — that is the guard that stops a forgotten mount silently writing a year of
results into a container that the next redeploy throws away. The abort message names this
escape hatch, so nobody has to guess. `tests/test_storage.py` pins all of it, including that
local mode *still* fails loud when the directory it was pointed at cannot be written.

To move to a volume later: mount the ASV, unset `STORAGE_MODE`, and copy your last export in
via the Admin page (or drop the SQLite file into the volume's `<app-slug>/` subdirectory).

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
DATA_DIR=$(mktemp -d) python -m pytest -q      # 138 tests
```

The suite includes the three load-bearing checks — `core/` imports with **no streamlit
installed**, every plot's "Show the code" **runs standalone** against an exported CSV, and
**60 simultaneous sessions** submit without error or cross-session leakage — plus a
`.adalab/` integrity suite that catches the deployment mistakes which otherwise only surface
at build or deploy time (container filename ≠ `uid`, two primary containers, a committed
secret, a `stripped_prefix`/`baseUrlPath` mismatch, resources outside the platform caps).

## Repository layout

```
lab-exercise-app-template/
├── copier.yml                  # the questions
├── README.md                   # this file
├── GETTING-STARTED-ADALAB.md   # step-by-step for the AdaLab lab terminal
├── DECISIONS.md      # decisions taken where the specs were silent/ambiguous
├── HANDOVER.md       # build report across the base spec + Addendum A + Addendum B
└── template/
    └── {{project_slug}}/   # the app that gets stamped out
```

## Design principles

1. **Chassis vs. seam**, enforced not just documented. The seam is Python only, so CPDSE
   scientists working with coding agents can own it for years.
2. **`core/` is framework-free** — the seed of the shared library later apps will depend on.
3. **Data durability**: append-only, close-never-delete, fail-loud storage, stable export
   columns across years.
4. **One visual identity**: CPDSE colours live only in `core/theme.py`.

See `Lab_Exercise_App_Template_Spec.md`, `..._Addendum_A.md` and `..._Addendum_B.md` for the
full specification (Addendum B wins on conflicts).
