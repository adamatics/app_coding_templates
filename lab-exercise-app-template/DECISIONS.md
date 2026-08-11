# DECISIONS

Decisions taken where the spec was silent or ambiguous, with a one-line rationale
each. Newest at the bottom of each section.

## Addendum A — reconciled against the ACTUAL text (was missing, later provided)

The addendum file was initially absent, so I first reconciled against the change table the
user described inline. The real `Lab_Exercise_App_Template_Addendum_A.md` was then provided
and I reconciled a **second time against its exact text**. Net changes from the first pass:

- **Base-path resolution moved to the FRONTEND** (`frontend/src/lib/basepath.ts`, resolving
  from `window.location.pathname` per §A1) — this **replaced** my earlier backend
  `X-Forwarded-Prefix` injection. Discarded: `backend/app/basepath.py`, the index-injection
  of `<base href>`/`window.__BASE_PATH__`, the forwarded-prefix middleware, and
  `meta.base_path`. AdaLab strips the prefix, so the backend serves at root and never needs
  to know it; the browser URL still carries `/apps/<slug>/`, which the frontend reads.
- **`.adalab/local_container_1.json` → `local_container_demo.json`** (the sibling-template
  filename in §A2), `container_description`/`app_description` now use a new `app_description`
  Copier question, and `maintainers: []` (was `[contact_email]`) to match §A2 verbatim.
- **`.vscode/settings.json`** = `{"adalab.workingMode": "appBuilder"}` added (§A1).
- **Guardrail reworked** from my earlier flat set to §A4's model: a granular protected set,
  a `permissions.ask` tier (`theme.css`, `.adalab/local_container_demo.json`, dependency
  manifests + `pip/npm install`), dangerous-bash blocks in the hook, a PostToolUse
  ruff+prettier hook, a SessionStart announcement, and `.claude/rules/*.md`. `theme.css` is
  now **ask** (editable with confirmation + `_skip_if_exists` on `copier update`), not deny.
- **A3 defensive IO** made concrete: `storage.py` filters `lost+found`/`.AVI_SUCCESS` and
  does write-temp-then-`replace` atomic writes; exports persist atomically to the volume with
  stable filenames; `GET /api/admin/exports` lists them through the filter.
- **copier `_tasks`** (`chmod +x` hooks, `git init -b main`) and **`_skip_if_exists`** on
  `theme.css` added (§A4).
- **README** gained the full ASV runbook (create → ACL → mount in lab → chown/chmod → mount
  with Fast Mount), the single-replica constraint, and the Test → Build → Deploy order (§A3).

Note: base spec §12 asked for `.adalab/card.json`; §A2 says "card.json … remains, unchanged",
so it is kept alongside the three-file convention.

## Addendum A reconciliation (supersedes conflicting base-spec decisions below)

- **Port is 8000 everywhere; the `app_port` Copier question is removed.** Supersedes the
  base-spec 8080 and the `app_port` question. `APP_PORT` env still defaults to 8000 for
  local flexibility but nothing asks for it.
- **`BASE_PATH` env var removed; base path resolved at runtime** from the request
  (`X-Forwarded-Prefix` header, else ASGI `root_path`, else `/`). Supersedes the earlier
  "runtime base injection driven by a `BASE_PATH` env" decision. One image now adapts to any
  mount prefix with zero configuration — the injected `<base href>`, the admin cookie path
  and the SPA router basename all follow the per-request value.
- **`DATA_DIR` defaults to `/asv-mnt/lab-data`** (AdaLab mount convention: platform mounts
  live under `/asv-mnt/`). Supersedes the base-spec `/data`.
- **Container runs Python 3.11** (was 3.12). `requires-python` relaxed to `>=3.11`; code
  kept free of 3.12-only syntax.
- **Fail-loud storage (§A3): `DATA_DIR` is never created by the app.** If it is missing or
  not writable the app refuses to start, naming the path and the volume-mount fix. Only
  *sub*-directories (e.g. `exports/`) are created inside it. Rationale: auto-creating
  `DATA_DIR` in a root container silently writes to disposable container-local storage and
  destroys data on the next redeploy — the exact failure the addendum calls out.
- **Guardrail is one canonical protected set expressed in three layers (§A4).**
  *(Superseded by the actual §A4: the set is now granular and there is a `permissions.ask`
  tier — see the top section. The "three layers name the same set" principle is unchanged.)*

## Repository / Copier

- **Generated app is nested under `<dest>/<project_slug>/`** (via `_subdirectory: template`
  and the `template/{{project_slug}}/` tree from spec §3). Rationale: the spec's own
  layout nests the app under its slug; gives each app in the family a self-contained named folder.
- **`config.py` is a Copier template (`config.py.jinja`)** so per-app identity values
  (exercise title, course code, host institution, contact email, default cohort label)
  are injected once at stamp time as defaults, still overridable by env vars. Rationale:
  spec §2 says "Copier injecting per-app variables"; these labelling values must reach the
  runtime and config is where env parsing already lives. It is still chassis (guard-blocked).
- **`theme.css` is fully static (no Copier injection).** Rationale: spec §4 ("no colour or
  logo questions") and §13 (fixed token file) override §2's loose "accent choice" parenthetical;
  keeping it static keeps the "no hex outside theme.css" rule clean.
- **Slug validation** is a lightweight Jinja validator (starts with a letter, lowercase,
  alphanumeric+hyphen). Rationale: avoids depending on optional regex Jinja filters.

## BASE_PATH / sub-path serving  *(SUPERSEDED by Addendum A §A1)*

The final design resolves the base path in the **frontend** (`frontend/src/lib/basepath.ts`
from `window.location.pathname`), with Vite `base: './'`; AdaLab (`stripped_prefix: true`)
strips the `/apps/<slug>/` prefix so the backend serves at root. See the top section. The
earlier backend `<base href>`/`window.__BASE_PATH__` injection was removed.

## Chassis guard

- **Guard uses a concrete chassis DENY list** covering all chassis code + config
  (`backend/**`, `frontend/src/**` except nothing — the whole `src` tree is chassis except it
  contains no seam files, `.adalab/**`, `Containerfile`, `pyproject.toml`, frontend build
  config, `.claude/**`) and ALLOWS the seam (`exercise/**`) plus top-level docs
  (`README.md`, `DECISIONS.md`, `HANDOVER.md`). Rationale: the user's #1 priority is that the
  hook actually blocks writes *outside the seam*; a deny list that covers every chassis file is
  the faithful reading of §11's list, extended to the rest of the chassis for completeness.
- **Blocks via exit code 2 + stderr** (Claude Code PreToolUse convention) and also emits the
  JSON `hookSpecificOutput.permissionDecision=deny` form for newer harness versions.

## Build decisions

- **`.adalab/` built to the REAL AdaLab convention** — `project.json`
  (`{"type":"appBuilder"}`), `app.json`, `local_container_1.json` — discovered from the
  installed `adalab-deploy` skill and real example apps, **plus** `card.json` from base §12.
  Rationale: the addendum corrects toward AdaLab realism and its §A2 text was unavailable;
  the three-file convention is the actually-deployable one, so it is almost certainly what
  §A2 specifies. `card.json` is kept because base §12 explicitly requires it and it is
  low-harm. The `local_container_<n>.json` filename suffix matches the internal `uid` (=1),
  per the extension's globbing rule. `stripped_prefix: true` matches the runtime base-path
  design (AdaLab's own "strip prefix" uses `X-Forwarded-Prefix` — exactly what the app reads).
- **`access_level: "logged_in"` in app.json** (a confirmed-valid value) with the README
  instructing deployers to set the app ACL to **Public** for students without AdaLab
  accounts. Rationale: ship a definitely-valid manifest; open student access is a one-line
  wizard change and is documented, safer than guessing an unverified `"public"` enum.
- **`volume_mounts: []`** in the container manifest, with the persistent-volume requirement
  surfaced prominently in the README (mount an Adalab Shared Volume at `/lab-data` →
  `/asv-mnt/lab-data`). Rationale: spec §12 says to surface the mount question, not solve it
  in code; the fail-loud guard enforces it at runtime.
- **Single `Containerfile`** (no duplicate `Dockerfile`); docs use `podman build` /
  `docker build -f Containerfile`. Rationale: avoid drift between two identical files;
  podman auto-detects Containerfile.
- **Demo data synthesised generically from the JSON Schema** (deterministic per cohort),
  not hard-coded for the worked example. Rationale: `DEMO_MODE` must keep working after an
  author changes `exercise/schema.py`.
- **Home renders `exercise/content.md`** via a new `GET /api/content` endpoint + the small
  `marked` library (teacher-authored content is trusted, so HTML rendering is acceptable).
  Rationale: §7 Home shows the seam's instructions; `marked` keeps the bundle small.
- **Charts are dependency-free inline SVG** (no chart library). Rationale: "keep the bundle
  simple" (§2) and it makes the §13 chart-colour rules trivial to enforce via CSS classes.
- **Correction (supersede) UI is inline on the Results page**; reuses `SchemaForm`.
  Rationale: the spec didn't pin the correction UI; this satisfies §15.3 with no new surface.
- **Chassis additions beyond the literal §3 layout**: `services.py` (the single home of the
  durability rules), `exercise_bridge.py` (the chassis↔seam boundary), `basepath.py`
  (runtime base resolution). Rationale: §3's file list is illustrative; isolating these
  makes the load-bearing rules testable in one place.
- **Concurrency-safe 409s**: `create_group`/`rename_group`/`create_cohort` wrap flush+commit
  so a uniqueness race surfaces as a clean 409, not a 500 (found by the concurrency test).
- **Session secret is ephemeral** (regenerated each startup, per §8 "derived at startup");
  admins simply log in again after a restart. No secret is written to disk.

## Verification environment

- **Container builds verified with Docker, not podman** (podman absent in the build env).
  The Containerfile is OCI-standard and the spec's `podman build/run` invocation works
  unchanged with `docker`; noted in HANDOVER.
