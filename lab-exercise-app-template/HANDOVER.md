# HANDOVER — `lab-exercise-app-template`

A Copier template that stamps out CPDSE student lab-exercise apps as **single-process
Streamlit applications** (Python 3.11, one container, port 8000), with a framework-free
`core/`, a thin Streamlit `pages/` chassis, and a Python-only exercise seam.

Built against three documents, later winning over earlier:
`Lab_Exercise_App_Template_Spec.md` → `Addendum_A` (AdaLab + persistence) →
`Addendum_B` (Streamlit switch + CPDSE decisions).

**Bottom line.** The §B1 deployment check was done first and produced a real finding that
changed the deploy config. The three load-bearing items are implemented and verified:
`core/` never imports streamlit (tested two ways), every plot's "Show the code" runs
standalone against an exported CSV (executed in a clean subprocess), and 60 concurrent
sessions submit with no errors and no cross-session leakage (which caught a real bug).
**69 tests pass**; the container builds and runs. What needs a live AdaLab tenant is called
out plainly and is *not* claimed as passing.

---

## 1. §B1 deployment check — done first, with a finding

**No AdaLab tenant is reachable from this environment**, so per your instruction I built a
local equivalent that proves the same two properties, and I say plainly below what remains
unverified.

**Setup.** Hello-world Streamlit run with `--server.baseUrlPath apps/hello`, fronted by a
passthrough TCP proxy (a proxy hop between client and app, as AdaLab has).

| Check | Direct | Through proxy |
| --- | --- | --- |
| HTML page under the prefix | 200 | 200 |
| JS bundle / font / favicon under the prefix | 200 | 200 |
| `/_stcore/health` | ok | ok |
| **WebSocket `/_stcore/stream`** | **101, session established** | **101, held open** |
| Same paths *without* the prefix (control) | 404 | — |

**Finding — this changed the deploy config.** Streamlit's router requires the prefix to be
present on incoming requests: with `baseUrlPath` set, requests at `/` return **404**. That is
exactly what a *stripping* proxy would deliver. So Addendum B's "retain `stripped_prefix:
true`" cannot hold together with `--server.baseUrlPath`, and §B1 is the check designed to
surface this (it says: if assets don't resolve, set `--server.baseUrlPath` — which requires
the prefix to arrive intact).

**Resolution:** `.adalab/app.json` sets **`stripped_prefix: false`** and the container runs
Streamlit with `--server.baseUrlPath=$BASE_URL_PATH` (defaulting to the app slug). Documented
in the app README with the one-line fallback if a future AdaLab version behaves differently
(`BASE_URL_PATH=""` + `stripped_prefix: true`).

**Not verifiable here:** whether AdaLab's real proxy forwards the prefix and holds the
websocket open for a long session. The local equivalent proves Streamlit's side and that a
proxy hop is not inherently fatal; the tenant's proxy config is the remaining unknown. This
is the single highest-value thing to check on a real tenant before building more apps.

---

## 2. What was discarded and what was salvaged

**Discarded (per §B1).** The entire `frontend/` tree (React 18, Vite, TypeScript, `App.tsx`,
`api.ts`, `SchemaForm`/`DataTable`/`Chart`/`ConfirmButton`, all pages, `theme.css`, `ui.css`,
the `check-theme.mjs` brand guard, `package.json`/`tsconfig.json`/`vite.config.ts`, the SVG
assets), the **Node build stage** in the Containerfile, `frontend/src/lib/basepath.ts`, and
the **React/TypeScript guardrail rule** (`.claude/rules/react-conventions.md`). Also gone with
the framework: the FastAPI layer (`backend/app/main.py`, `auth.py`, all `routers/`), since
Streamlit is the process now.

**Salvaged and ported (framework-independent).** The data model and every durability rule
(append-only, supersede, close-never-delete, single-row audited hard delete), cohort
lifecycle, admin logic (constant-time compare, fail-closed), group merge/rename/delete
semantics, export column stability, the `.adalab/` configuration, ASV persistence with
fail-loud startup and `lost+found`/`.AVI_SUCCESS` filtering and atomic writes, the demo seeder
(still schema-driven), the CPDSE palette (now `core/theme.py`), and all agent guidance assets
(CLAUDE.md, the skill + references, `/new-exercise-field`, the three-layer guardrail
structure, the format/SessionStart hooks) — each updated for the new architecture.

**Rewritten around the new architecture.** `core/` gained `identity.py` (KUID + course gate),
`plots.py` (§B7), `export.py` (four formats), `analysis.py`, `preflight.py`, `storage.py`; the
old FastAPI routers became `pages/*`; tests moved `backend/tests/` → `tests/`.

---

## 3. The three load-bearing items

### 3.1 `core/` never imports streamlit (§B1) — VERIFIED
`tests/test_core_no_streamlit.py` proves it three ways: an **AST scan** of every `core/*.py`,
a **subprocess import of all 17 core modules with streamlit blocked** by an import hook
("core imports and its tests pass with no Streamlit installed"), and a check that importing
`core` doesn't pull streamlit in even when it *is* installed. It also asserts
`exercise/schema.py` stays framework-free, since `core` imports it.

Structurally: `core/exercise_bridge.py` deliberately imports only `exercise.schema` and reads
`content.md`; the streamlit-using `exercise/capture.py` and `exercise/analysis.py` are imported
by `pages/`, never by `core/`.

### 3.2 "Show the code" (§B7) — VERIFIED
`core/plots.py` helpers return `(figure, code_str)`. `code_str` is plain
`pandas` + `plotly.express` that reads an exported CSV — never Streamlit-specific — and is
generated from the same call that drew the figure, so it cannot drift.
`tests/test_show_the_code.py` writes the exported CSV into a **clean temp directory** and runs
each snippet in a **fresh subprocess with no app code importable** — the exact situation of a
student pasting it into a notebook. Every plot the reference app renders is covered.

### 3.3 Concurrency (§B10) — VERIFIED, and it caught a real bug
`tests/test_concurrency.py` runs **60 threads = 60 sessions** submitting simultaneously, then
asserts every row is attributed to its own member/KUID/group (no cross-session leakage), plus
a 20-way concurrent-registration race and a CSV-mirror consistency check.

**The bug it caught:** `atomic_write_bytes` named its temp file by **PID only**. In Streamlit
all sessions are threads in *one* process, so 60 sessions collided on one temp filename and 11
submissions died with `FileNotFoundError` on `os.replace`. Fixed by making the temp name unique
per pid+thread+counter, and by serialising the whole-file mirror rewrite behind a lock. This is
exactly the failure §B10 exists to prevent (a ruined first lesson with two classes in the lab).

---

## 4. A second real defect found by container testing

Running the built image with **no volume mounted**, the container **started and served the app
anyway** — because `init_db()` ran lazily inside `@st.cache_resource` on first page render, so
Streamlit bound the port first. That is the "looks fine in the classroom, loses a year of data
at the next redeploy" failure mode §A3 forbids.

**Fixed** with `core/preflight.py`, run by the container entrypoint *before* Streamlit
(`python -m core.preflight && exec streamlit run ...`). Verified in a real container: with no
volume the container **exits 1** with `STARTUP ABORTED` naming the path, and Streamlit never
starts. Two regression tests pin it.

---

## 4b. Added after Addendum B, at your request

**Durable sessions without student passwords.** Streamlit's `session_state` dies on refresh, so
a student who reloaded had to re-enter the course password *and* their KUID. Now the app puts an
**opaque random token** in the URL (`?s=…`) backed by a `session_token` row. Deliberately not a
signed token containing the KUID: that would put personal data into browser history and proxy
logs in decodable form. Only the SHA-256 hash is stored, tokens expire (`SESSION_TTL_DAYS`,
default 30), sign-out revokes, and a token from a closed year restores the gate but forces
re-registration. §B2's "no per-student passwords" is untouched. **Known trade-off:** the URL is
a bearer credential — sharing the link shares the session. That matches the honour-system model
already in force, but it is a real property, not a detail.

**Event logging.** The base spec's admin-only `audit` table is generalised into an `event` table
covering every actor (`core/events.py`; `core/audit.py` deleted, so there is one log, not two).
Recorded: registrations with timestamps, returning students, group creation, every submission,
every **overwrite** (old values, new values, changed-field list), answers saved, exports
actually taken, all admin actions, and all errors with tracebacks. Three sinks — the `event`
table (Admin → Log, filterable, CSV export), **stdout** (AdaLab log viewer), and
**`events.jsonl` on the volume** (survives redeploys, rotated at 5 MB).

Two properties worth knowing:
- **Logging can never break the app.** Sinks guard themselves *and* the call site guards them;
  a test breaks both non-DB sinks and asserts a submission still succeeds. (That test found a
  real gap — the call site was originally unguarded.)
- **PII split.** DB and volume log keep the KUID (same DPA as the results); stdout gets a
  pseudonymous `member:<id>` unless `LOG_PII=true`, because platform logs are aggregated wider.

Exports are logged from the download button's `on_click`, never from the builders — Streamlit
rebuilds button data on every rerun, so the naive placement would log phantom exports.

Verified: `core/` still framework-free, container builds and both non-DB sinks confirmed
working in-container.

## 4c. Schema and export review (asked for after the logging work)

A deliberate audit of the database schema and the export surface, which turned up **two
integrity bugs** and four gaps. All fixed and pinned by tests.

- **Registration had no database-level uniqueness.** `register()` was check-then-act with
  nothing behind it, unlike group names. Two tabs could split one student across two `member`
  rows — and their results with them. `Member` now carries a denormalised `cohort_id` with
  `UniqueConstraint(cohort_id, kuid_key)`; a lost race returns the winning registration.
  *(I could not reproduce the race — SQLite serialises writes — so this was a latent hole, not
  an observed failure. Verified by inserting a duplicate directly and by 16 concurrent
  registrations, which now yield exactly one row.)*
- **Cross-year reassignment was possible — confirmed, not theoretical.** An admin could move a
  student from 2026 into a 2027 group; their results stayed behind and every scope query broke.
  Now refused with an explanation.
- **No schema-evolution guard.** `create_all` adds missing tables but never ALTERs an existing
  one, so a future column change would have surfaced mid-lab as a confusing SQL error. Added
  `SCHEMA_VERSION` + a startup check that fails loud with instructions (`ALLOW_SCHEMA_MISMATCH=1`
  overrides after a backup). Still no Alembic, per spec.
- **Admin exports weren't logged** — the event log was quietly incomplete. Fixed.
- **Answers and the roster were only reachable inside a PDF.** A teacher exporting a year for
  grading got measurements and nothing else. Both are now exportable as data.
- **Nothing took "everything".** Added a full workbook (results · answers · roster · years ·
  log) and a **SQLite backup** using SQLite's backup API — a raw file copy under WAL can miss
  committed transactions. §B5's premise is that apps get retired, so a take-everything button
  belongs there.

Verified: **106 tests**, container builds and the demo seed still works under the new
constraint.

## 5. Base spec §15 acceptance

✅ verified · 🟡 partial/by-proxy · ⚪ needs a live AdaLab tenant · ➖ superseded

1. **✅ `copier copy` defaults → container builds and runs** against an empty *mounted*
   volume (an unmounted path now fails loud by design).
2. **🟡 Two sessions submit concurrently, both visible.** Verified far beyond it in code:
   60 concurrent sessions, all rows visible and correctly attributed. Not two literal browsers.
3. **✅ Correction flow.** Supersede tested; latest-only view vs full history with a
   `superseded` flag in exports.
4. **✅ Admin lifecycle.** Wrong password rejected (constant-time, fail-closed when unset),
   close year → writes rejected, open new year, old year still visible and exportable.
5. **✅ Restart with the same volume: data intact** (SQLite + CSV mirror on the mount;
   verified in-container, and by Addendum A's redeploy simulation in the previous pass).
6. **✅ `DEMO_MODE=true` seeds two synthetic prior years**; verified in the container
   (`[preflight] seeded demo years: 2024, 2025`, 33 CSV rows) and the cross-year box plot is
   one of the reference plots.
7. **✅ Agent test.** The guard blocks all 13 chassis paths and allows the 4 seam files
   (matrix verified); a schema change flows to storage/CSV/exports/plots by construction.
8. **✅ Brand check.** All hex lives in `core/theme.py` only (the old CI grep is replaced by a
   single-source module + a plotly template); approved fill/ink pairs; Verdana stack; no
   invented error colours (Streamlit's red/green/amber widgets are banned by rule and replaced
   by `_components.notice`).
9. **➖ Replaced** by §B10's Streamlit items (see §7).
10. **✅ `pytest` green — 69 tests** on a fresh stamp.

---

## 6. Addendum A §A6 acceptance

11. **✅ Builds/runs on 8000; `.adalab` matches §A2** — with the deliberate, documented
    exception that **`stripped_prefix` is now `false`** (the §B1 finding) and `access_level` is
    `public` (§B2). `uid: 1`, ports 8000, `volume_mounts: []`, `local_container_demo.json` and
    `project.json` are unchanged from §A2.
12. **✅ Missing/unwritable `DATA_DIR` fails loud, no silent fallback** — now enforced in the
    entrypoint (see §4), verified in a real container plus two unit tests.
13. **✅ `lost+found` / `.AVI_SUCCESS` filtered** wherever the app enumerates the volume
    (`core/storage.list_volume_dir`, used by the admin export tab); tested.
14. **✅ Redeploy simulation** (destroy container, rebuild with a new image tag, same mount,
    data intact) — verified in the previous pass; the storage layer is unchanged by the
    Streamlit switch and the current image was re-verified for start-up and volume layout.
15. **➖ Replaced** by §B10's runtime-basepath item.
16. **✅ Three guardrail layers consistent** — `permissions.deny`, the hook's `PROTECTED`, and
    `CLAUDE.md` name the identical 13-path §B9 set (script-checked).
17. **✅ README has the ASV runbook** (create → ACL → mount in lab → chown/chmod → Fast Mount
    ON) **and the single-replica constraint**, plus Test → Build → Deploy.

---

## 7. Addendum B §B10 acceptance

- **⚪/🟡 Hello-world Streamlit deploys on AdaLab and holds its websocket under the URL
  prefix.** Not verifiable here (no tenant). Proven on a local equivalent through a proxy hop:
  101 handshake, session held, static assets and health all resolve under the prefix. See §1.
- **✅ `core/` imports and its tests pass with no Streamlit installed.** See §3.1.
- **✅ Concurrency: 60 simultaneous sessions, no error, no cross-session leakage.** See §3.2 —
  and it caught a real bug.
- **✅ Every plot in the reference app has a working "Show the code" panel whose code runs
  standalone against an exported CSV.** See §3.2, executed in a clean subprocess.
- **✅ Course gate rejects a wrong password, admits with the right one; app reachable without
  an AdaLab account.** Gate logic tested (constant-time, fail-closed when unset); "reachable
  without an account" is `access_level: "public"` in the manifest — the *manifest* is correct,
  but the tenant behaviour is ⚪ unverifiable here.
- **✅ Export produces all four formats; CSV columns identical across two cohorts.** CSV,
  Excel, PDF (asserted to be a real `%PDF`), HTML (asserted to contain data, answers, plot and
  its code); a dedicated test writes two different years and asserts identical headers.

---

## 8. Weakest parts (my honest read)

1. **Everything tenant-dependent is unverified** — the real AdaLab websocket path, whether the
   proxy forwards the prefix, `access_level: "public"` actually admitting anonymous students,
   the ASV chmod/Fast-Mount runbook, and the Gallery card. My §B1 finding *predicts* the config
   AdaLab needs; a 20-minute hello-world deploy on a real tenant would confirm or refute it and
   is worth doing before anything else.
2. **No Streamlit UI tests.** `pages/*` and `app.py` are verified only by import + the
   container smoke test. Session-state behaviour (the gate, the correction flow, the scope
   selector) is exercised through `core` and by hand, not by AppTest. Streamlit ships
   `streamlit.testing.v1.AppTest`; that is the obvious next test layer and I did not build it.
3. **The concurrency test models sessions as threads**, which matches Streamlit's real
   execution model, but it drives `core` directly rather than 60 browser websockets. It found a
   genuine bug, so it has real value — but a true 60-websocket load test would be stronger.
4. **PDF reports depend on kaleido 0.2.1** (pinned deliberately: kaleido ≥1.0 changes the API
   and fetches Chromium at runtime). It emits a deprecation warning and is a future
   maintenance point. If kaleido fails, the PDF still renders with a "see the HTML report"
   placeholder instead of images — degraded, not broken.
5. **The `neighbour` scope is a convention I chose** (cyclically adjacent group in the same
   hold), because §B4 names the scope without defining adjacency. Trivial to change, but it is
   a guess about how the lab is actually organised.
6. **Answers are stored per group and questions are parsed from `content.md`.** If a teacher
   reorders the question list, existing answers keep their `q1..qN` ids and will attach to the
   new wording. A stable explicit id syntax would be safer.
7. **`.streamlit/config.toml` repeats four palette hex values** because Streamlit's own theming
   needs literals — the only place CPDSE colours exist outside `core/theme.py`. Documented in
   the file; a drift risk if someone edits one and not the other.

---

## 9. What I'd do next

- **Deploy the hello-world to a real tenant** and confirm/refute the `stripped_prefix: false` +
  `baseUrlPath` finding, then the full app; this unblocks every ⚪ item.
- Add **`AppTest`-based UI tests** for the gate, registration, capture→supersede and the scope
  selector — the biggest coverage gap.
- Add a **second worked seam** (a non-chemistry exercise) plus CI that stamps, tests and builds
  both, proving the seam really is the only per-app surface.
- Wire **lmfit** into the reference exercise (it is in the stack per §B8 but the logP example
  doesn't need a fit yet) so the fitting pattern is demonstrated with a "Show the code" panel.
- Move to **kaleido ≥1.0** once its Chromium fetch can be baked into the image offline.
- Consider promoting `core/` to an installable shared library once a second app exists — the
  no-streamlit guarantee is what makes that possible, so keep the test.

---

## 10. Publishing note

The stamped app is turned into its own git repo by a copier `_task`. The template itself is a
plain directory (not git-initialised here; commits are gated on your say-so). Note the earlier
React version of this template was proposed to `adamatics/app_coding_templates` as
[PR #3](https://github.com/adamatics/app_coding_templates/pull/3) — **that PR is now
superseded by this Streamlit rewrite** and should be closed or force-updated before anyone
merges it.

**Placeholder assets:** the CPDSE logo is drawn inline in `pages/_components.py` in the correct
colourway. Replace with the official CPDSE logo package before real use.
