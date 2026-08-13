# DECISIONS

Decisions taken where the spec was silent or ambiguous, with a one-line rationale
each. Newest at the bottom of each section.

## Addendum B — Streamlit switch (supersedes React where conflicting)

- **§B1 deployment check (done FIRST) — finding: Streamlit needs `stripped_prefix: FALSE` +
  `--server.baseUrlPath=<app_url>`.** No AdaLab tenant is reachable from this environment, so
  I proved the same properties on a local equivalent: hello-world Streamlit run with
  `--server.baseUrlPath apps/hello`, fronted by a passthrough TCP proxy. Verified under the
  prefix: HTML 200, JS/font/favicon 200, `/_stcore/health` ok, and the WebSocket
  `/_stcore/stream` completes the 101 handshake **and survives the proxy hop**. Converse
  proven: a request without the prefix (what a *stripping* proxy would deliver) → 404. So
  Streamlit's router requires the prefix on incoming requests; the proxy must forward it.
  **This overrides Addendum B's "retain stripped_prefix: true"** — B1 is exactly the check to
  discover this, and B1 itself says "if assets don't resolve, set --server.baseUrlPath" (which
  requires non-stripping). `.adalab/app.json` therefore sets `stripped_prefix: false`, and the
  container runs Streamlit with `--server.baseUrlPath=<project_slug>`. Real AdaLab proxy WS
  behaviour is not verifiable here (no tenant) — flagged in HANDOVER.
- **Architecture (§B1, non-negotiable):** `core/` framework-free (imports streamlit NOWHERE,
  proven by a test), `pages/` thin Streamlit chassis UI, `exercise/` the seam (Python, may use
  streamlit), `app.py` entry/gate/nav.
- **`access_level: "public"` (§B2)** now that the course-password gate is the control; resolves
  Addendum A's open access question.
- **Storage (§B6):** SQLite (system of record) + a long-format CSV mirror rewritten on every
  submission, both under `DATA_DIR`; each app under a per-app subdirectory of the shared ASV.
- **PDF library: reportlab** (pure-Python, headless, no system libs) + **kaleido** for plotly
  static images; the HTML report embeds interactive plotly. Rationale: §B8 wants a headless
  PDF lib; reportlab needs no system packages in `python:3.11-slim`, unlike weasyprint.
- **Identity model:** `cohort` = Year (one open); `group` carries `hold` (1–7); `member`
  carries KUID; results link to a member and derive KUID/group/hold/year via joins so any view
  can filter at any level (§B2). Course settings live in a key-value `setting` table (§B6).
- **`app.py` does its own sidebar navigation** instead of Streamlit's magic multipage
  auto-discovery. Rationale: §B1 fixes `pages/` as a *package of chassis UI modules*; letting
  Streamlit auto-register them as pages would bypass the course gate (deep links) and expose
  internals like `_components`. One entry point means the gate and banner can't be skipped.
- **`exercise/capture.py` returns a payload dict, it does not write.** The chassis validates
  against `exercise/schema.py` and stores. Rationale: keeps every durability rule in `core/`
  even though the seam now owns UI code.
- **Analysis questions are parsed from `content.md`** (the list under `## Analysis questions`),
  each getting a stable id `q1, q2, …` stored in an `answer` table per group. Rationale: §B3
  says the teacher's questions come from `content.md` and answers are stored alongside
  measurements; a stable id avoids re-keying answers when wording changes.
- **Answers are stored per GROUP** (not per individual). Rationale: §B5's report is the
  group's report, approved in-session; group-level answers match how the work is done.
- **The "neighbour" scope is the cyclically-adjacent group in the same hold+year.** Rationale:
  §B4 names the scope but not how a neighbour is chosen; deterministic and needs no config.
- **`_write_counter` + thread id in atomic temp filenames, and a lock around the CSV mirror
  rewrite.** Found by the §B10 concurrency test: a PID-only temp name makes 60 in-process
  Streamlit sessions collide (`FileNotFoundError` on `os.replace`). This is the exact class of
  bug §B10 exists to catch.
- **Streamlit's `st.error/success/warning/info` are banned** in favour of
  `pages._components.notice`. Rationale: they render off-palette red/green/amber; §13 says the
  palette has no red or amber and state is conveyed with words and weight.
- **`core/theme.py` is the single hex source** (replacing `theme.css`), consumed by the plotly
  template, the injected CSS and the reports. `.streamlit/config.toml` necessarily repeats the
  four theme colours as literals because Streamlit's own theming needs static values —
  documented in that file.
- **kaleido is pinned to 0.2.1** for PDF plot images. Rationale: kaleido ≥1.0 changes the API
  and pulls a Chromium download at runtime, which is wrong for an offline container build.
  Plotly emits a deprecation warning; noted in HANDOVER as a follow-up.
- **Tests moved from `backend/tests/` to `tests/`** at the app root, matching the new layout.

## Durable sessions without student passwords (post-B request)

- **Opaque random token in the URL (`?s=…`), backed by a `session_token` row** — chosen over a
  self-contained signed token. Rationale: a signed token would carry the KUID in decodable form
  into browser history and proxy logs; KUID is personal data under the KU DPA. An opaque token
  keeps personal data out of URLs entirely and gives revocation for free. Only the SHA-256
  **hash** is stored, so a database copy yields no usable tokens.
- **No per-student passwords** — §B2 forbids them; this only removes the re-entry friction on
  refresh, it does not add a credential the student must remember.
- **A token from a closed year restores the gate but not the identity**, forcing re-registration
  in the new year rather than silently writing to a closed cohort.
- **TTL 30 days (`SESSION_TTL_DAYS`)**, purged at startup. Rationale: §B4 expects students to
  return "weeks later" while writing their report.
- **Known trade-off:** the URL is a bearer credential — sharing the link shares the session.
  This matches the honour-system model already in place (anyone past the gate can type another
  KUID), and is mitigated by the TTL and revoke-on-sign-out. Recorded in HANDOVER as a weak spot.

## Event logging (post-B request)

- **One log, not two: the base spec's admin-only `audit` table is generalised into an `event`
  table** covering every actor (`core/audit.py` deleted, `core/events.py` added). Rationale:
  two overlapping logs is worse than one; the event log is a strict superset of what §5 asked
  for, and the admin "Audit" tab became a richer "Log" tab.
- **Three sinks**: the `event` table (teacher-facing, filterable, CSV-exportable), **stdout**
  via `logging` (operator-facing, lands in the AdaLab log viewer), and **`events.jsonl` on the
  shared volume** (survives redeploys, which stdout does not; size-rotated at 5 MB).
- **Logging can never break the app.** Each sink guards itself *and* the call site guards the
  sinks; a failed log costs a log line, never a measurement. Pinned by a test that breaks both
  non-DB sinks and asserts a submission still succeeds.
- **PII split: stdout gets a pseudonymous `member:<id>`, the DB and volume log keep the KUID**
  (`LOG_PII=true` overrides). Rationale: platform logs are aggregated more widely than the
  app's own volume; the KUID belongs with the results it describes, under the same DPA.
- **Exports are logged from the button's `on_click`, never from the builders in `core/export.py`.**
  Rationale: Streamlit rebuilds `st.download_button` data on every rerun, so logging in a
  builder would record exports nobody took. Pinned by a test.
- **Overwrites record old values, new values and the changed-field list**, so a correction is
  fully reconstructable — the append-only table already keeps both rows, and the log explains
  *what* changed without diffing payloads by hand.
- **A page-level error boundary in `app.py`** logs any unexpected exception with its traceback
  and shows a plain message, instead of a raw stack trace (or, with `showErrorDetails=false`,
  a blank panel that tells nobody anything).

## Teacher-facing surface (post-B request)

- **The two seam pages ship as annotated teaching templates, not bare examples.**
  `exercise/capture.py` and `exercise/analysis.py` now open with a header explaining what the
  file is, the contract it must satisfy, and how to write a good one, with the logP worked
  example retained below and an "ADD YOUR OWN BELOW" marker. Rationale: these are the two
  files a teacher (usually with an agent) rewrites per course; the file itself is where they
  will look, not the docs.
- **`exercise/capture.py` may export an optional `render_intro()`** shown above the form, so
  the exercise can tell students what to have ready at the bench. Optional and called
  defensively — an author who deletes it loses nothing.
- **Document upload is a new feature, not just documentation.** The `documents` setting only
  ever held URLs; a teacher had no way to put the øvelsesvejledning *in* the app. Added a
  `document` table + `core/documents.py` + admin manager + student download surfaces.
  A new table needs no `SCHEMA_VERSION` bump — `create_all` adds it.
- **Files are stored on the volume under an id prefix (`0001_name.pdf`), never by raw name.**
  Filenames are sanitised (no traversal, no separators), size-capped at 20 MB to match
  Streamlit's upload limit, and written atomically like every other volume write.
- **Documents are deliberately outside the SQLite backup.** They are files, not rows; the
  teacher already has the originals. Stated in the backup caption and the README rather than
  silently implied.
- **Admin help is inline, not a manual.** Each admin element is a numbered expander explaining
  what it does, when to use it, and what students see — a teacher configuring the app under
  time pressure reads what's on screen, not a README.

## AdaLab conformance review (against the platform's app-builder guidance)

Reviewed `.adalab/` against the platform's own app-builder reference. Distilled only the rules
this template depends on — the plugin is internal and is not reproduced here.

- **`local_container_demo.json` → `local_container_1.json` (bug fix).** The platform requires
  the filename's integer suffix to equal the `uid` field; a file named after the image is the
  documented cause of duplicate-container deploys ("stop the deploy"). Addendum A §A2 named the
  file `_demo` while also specifying `uid: 1` — the two can't both hold, and the platform rule
  wins because it is what the tooling keys off.
- **`max_ram` 500 → 1500 MB.** 500 is the scaffold default; this container runs Streamlit +
  pandas + plotly + reportlab + kaleido, and PDF rendering in particular would risk OOM.
  Platform cap is 2000.
- **`project.json` gains `author` and `id`.** The platform shape is `{type, author, id}`;
  Addendum A §A2 showed only `type`. `author` is the owning AdaLab user (LOGNAME), which a
  template can't know, so a copier `_task` fills it from `$LOGNAME` after generation (Copier
  has no `env` filter — verified).
- **`container_file` `./Containerfile` → `Containerfile`, `build_context` `./` → `.`** to match
  the platform's own scaffold exactly.
- **`project_slug` validator tightened to the real `app_url` rule**
  (`^[a-z0-9]([-a-z0-9]*[a-z0-9])?$`, ≤ 63 chars). Previously a trailing hyphen or an over-long
  slug would pass here and fail at deploy time, long after stamping.
- **`tests/test_adalab_config.py` — 16 checks that run with the normal suite.** Encodes the
  platform's folder-integrity pre-flight (filename↔uid, unique uids and image names, exactly
  one primary, `app_id`/`metadata_id` null, valid `app_url`, resource caps, no reserved env
  vars, no committed secrets, `mount_path` without leading/trailing slash, at most one Fast
  Mount) plus a check that `stripped_prefix` stays consistent with `--server.baseUrlPath` and
  that `DATA_DIR` matches the documented mount path. Rationale: every one of these fails *late*,
  at build or deploy, often in front of a class — a test moves the failure to the repo.
- **Kept the fail-loud storage check rather than the platform's generic `ensure_volume_ready`
  pattern**, which does `mkdir(parents=True)` first. On an unmounted path that silently creates
  a container-local directory — precisely the data-loss mode this template exists to prevent.
- **`stripped_prefix: false` is now corroborated**, not just inferred from my §B1 experiment:
  the platform's own troubleshooting states the prefix-aware/root-serving choice is
  all-or-nothing and must not be mixed.

## Preview mode (fix: AdaLab Test could never pass)

- **Symptom:** the extension's Test step builds fine, starts the container, and it exits
  immediately — `CONTAINER_READINESS_FAILED` after 5 attempts. Test runs the image with
  `"Env": []` and no volume mounts, purely to check the app serves; the fail-loud storage
  guard then correctly refused to start. So the app could never pass the documented
  Test → Build → Deploy order.
- **Fix:** the safety property is not "a volume must always be mounted", it is "student data
  must never land on disposable storage". Students cannot reach any page without
  `COURSE_PASSWORD` (the gate fails closed), so nothing can be collected without it. Therefore:
  `COURSE_PASSWORD` set → a writable volume is **required** (fail loud, unchanged);
  `COURSE_PASSWORD` unset → run on scratch space in **preview mode**, announced in the
  container log and as a banner on every screen.
- The dangerous case — a real deployment that forgets the volume — still refuses to start.
  Verified in containers for all three cases, and pinned by three tests.
- Rationale for choosing the course password as the sentinel rather than an opt-out env var:
  Test sets *no* environment at all, so any opt-out flag would have to default to permissive,
  which would defeat the guard entirely.

## Schema and export review (post-B)

- **`Member` carries a denormalised `cohort_id` + `UniqueConstraint(cohort_id, kuid_key)`.**
  Registration was a check-then-act ("look up the KUID, then insert") with nothing behind it,
  unlike group names which had a constraint. Two tabs could have split one student across two
  member rows — and their results with them. The DB now holds the invariant; a lost race
  returns the winning registration instead of an error.
- **`reassign_member` refuses cross-year moves.** It previously let an admin move a student
  from 2026 into a 2027 group (verified), which stranded their results in the old year and
  broke every scope query. A student in two years is two registrations, not one member moved.
- **Schema version guard (`SCHEMA_VERSION` + `_schema_version` setting).** `create_all` adds
  missing tables but never ALTERs an existing one, so a changed column would have surfaced
  mid-lab as a baffling SQL error. Startup now fails loud with instructions, matching the
  storage stance. `ALLOW_SCHEMA_MISMATCH=1` overrides after a backup. Deliberately still no
  Alembic (§B8 / base spec).
- **Admin exports are logged too.** Only the student-facing exports were, which made the new
  event log quietly incomplete.
- **Answers and roster are exportable as data, not just inside a report.** A teacher exporting
  "all years" for grading previously got measurements only; the free-text answers were reachable
  only by opening each group's PDF.
- **Added a full workbook (results · answers · roster · years · log) and a SQLite backup.**
  §B5's premise is that apps get retired and the export is what people keep — that argues for
  a "take everything" button. The backup uses SQLite's backup API, not a file copy, because a
  raw copy under WAL can miss committed transactions.

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
