# HANDOVER — `lab-exercise-app-template`

A Copier template that stamps out CPDSE student lab-exercise apps: a FastAPI + SQLite backend
and a React 18 + Vite + TypeScript frontend served by the **same** process (one container,
port 8000), the CPDSE visual identity, append-only cohort-based persistence, an admin area,
CSV/Parquet export, and agent guidance with a three-layer chassis guardrail. Built against
`Lab_Exercise_App_Template_Spec.md` **and** `Lab_Exercise_App_Template_Addendum_A.md` (the
addendum wins on conflicts).

**Bottom line:** the two load-bearing goals — the chassis/seam split and data durability —
are implemented and verified, including in a real Python-3.11 container and a redeploy
simulation. The addendum's AdaLab conventions (§A1–A4) are implemented to the letter of its
text. What I can't verify is anything requiring a live AdaLab tenant; that's called out below.

---

## 1. The addendum: missing, then provided, reconciled twice

`Lab_Exercise_App_Template_Addendum_A.md` was absent when I started, so I first reconciled
against the change table described inline in the instructions. The real file was then
provided and I reconciled a **second time against its exact text**. The second pass changed
several things I had guessed at — details in `DECISIONS.md` ("Addendum A — reconciled against
the ACTUAL text"). The most significant:

- **Base-path resolution is now in the FRONTEND** (`frontend/src/lib/basepath.ts`, from
  `window.location.pathname`, §A1), replacing my earlier backend `X-Forwarded-Prefix`
  injection. That backend module, the `<base href>`/`window.__BASE_PATH__` injection, and
  `meta.base_path` were **discarded**. AdaLab's `stripped_prefix: true` strips the prefix, so
  the backend serves at root and never needs to know it; the browser URL keeps the prefix,
  which the frontend reads.
- `.adalab/local_container_1.json` → **`local_container_demo.json`**, with a new
  `app_description` Copier question and `maintainers: []`, to match §A2 verbatim.
- The guardrail was **reworked** to §A4's richer model (granular deny set + a `permissions.ask`
  tier + dangerous-bash blocks + PostToolUse formatting + SessionStart + `.claude/rules`).

Nothing from the durability core (models, services, routers, most tests) had to be discarded.

---

## 2. What I built (map)

- **Chassis backend** (`backend/app/`): `main.py` (API + static), `config.py.jinja`,
  `db.py` (WAL + fail-loud storage), `models.py`, `services.py` (the single home of the
  durability rules), `auth.py`, `exercise_bridge.py` (chassis↔seam boundary), `storage.py`
  (volume IO), `seed_demo.py`, `routers/{public,admin,export}.py`.
- **Exercise seam** (`exercise/`): `schema.py` (a worked absorbance example), `analysis.py`,
  `content.md` — the only files an author edits.
- **Chassis frontend** (`frontend/src/`): `App.tsx` shell, `lib/basepath.ts`,
  `components/{SchemaForm,DataTable,Chart,ConfirmButton}.tsx`, `pages/*`, `theme.css`
  (identity tokens), `ui.css`, and the `check-theme.mjs` brand guard.
- **Deploy**: `Containerfile` (Node 20 build → `python:3.11-slim`), `.adalab/{project,app,
  local_container_demo,card}.json`, `.vscode/settings.json`.
- **Agent assets**: `.claude/CLAUDE.md`, `settings.json` (deny/ask + 3 hooks),
  `hooks/{chassis_guard,format,session_start}.py`, `rules/*.md`, the `lab-exercise-app`
  skill (+3 references), and the `/new-exercise-field` command.

---

## 3. Decisions worth your attention

Full list in `DECISIONS.md`. Highlights:

- **Base path is frontend-resolved** from the URL; the backend serves at root behind
  AdaLab's stripped prefix. One build runs at `/` or `/apps/<slug>/`.
- **`.adalab` matches §A2 exactly** (`stripped_prefix: true`, `uid: 1`, `local_container_demo.json`,
  `maintainers: []`); `access_level: logged_in` ships as the safe default with the README
  telling teachers to switch it to `public` for classes.
- **Storage is fail-loud** and the app **never creates `DATA_DIR`** — a missing/unwritable
  volume stops startup with a message + the mount fix; sub-dirs only are created inside.
- **The guardrail hook is the real enforcement** (deny/ask lists are advisory). `theme.css`
  and `.adalab/local_container_demo.json` are **ask** (editable with confirmation), not deny.
- **Session secret is ephemeral** (§8 "derived at startup"); admins re-login after a restart.

---

## 4. How to run the verification yourself

```bash
copier copy --defaults --trust lab-exercise-app-template /tmp/out
cd /tmp/out/absorbance-lab

# Backend tests (pip install fastapi uvicorn sqlalchemy pydantic itsdangerous pandas pyarrow pytest httpx)
DATA_DIR=$(mktemp -d) python -m pytest -q            # 41 passed

# Frontend build (no-hex brand check + type-check + vite)
cd frontend && npm install && npm run build && cd ..

# Container, with the required volume
podman build -t app .                                # or docker build -f Containerfile -t app .
mkdir -p ./lab-data
podman run -p 8000:8000 -v ./lab-data:/asv-mnt/lab-data -e ADMIN_PASSWORD=secret -e DEMO_MODE=true app
```

Container builds were verified with **Docker** (podman absent here); the Containerfile is
OCI-standard and the podman invocation works unchanged.

---

## 5. Base spec §15 acceptance — results

✅ verified · 🟡 verified by proxy · ⚪ needs a live AdaLab tenant.

1. **✅ `copier copy` defaults → builds container, runs with an empty (mounted) `DATA_DIR`.**
   Clean generation (0 unrendered `.jinja`); image builds on Python 3.11; a fresh empty
   volume yields DB + tables + first cohort. Post-addendum, "empty `DATA_DIR`" means an empty
   *mounted* volume; an unmounted path fails loud by design.
2. **🟡 Two sessions, concurrent submit, both visible.** `test_concurrency.py` runs 30
   concurrent writers; all persist. Not two literal browsers, but the API/DB path is proven
   under real thread concurrency.
3. **✅ Supersede; latest shown; history export flags both.** Tests + manual container check.
4. **✅ Admin lifecycle.** Verified live in the container: wrong pw 401, correct 200, close
   409-on-write, open new, old cohort exportable.
5. **✅ Kill + restart same volume → intact.** Verified live (and see §A6.14).
6. **✅ `DEMO_MODE` seeds two prior cohorts; compare renders.** Cohorts seeded (14 each);
   `cohort=all` feeds the per-cohort compare chart. Chart correctness via build + logic +
   data, not a pixel screenshot.
7. **✅ Agent test (add field / block chassis).** The hook blocks all chassis paths and allows
   the seam (matrix verified); export columns follow schema field order (`test_seam.py`). No
   live Claude Code agent session was run inside a stamped app.
8. **✅ Brand check.** `check:theme` passes and gates the build. Approved fill/ink pairs; the
   header title uses §13's directed Soft-White-on-Forest (high-contrast; noted in the app
   README). Charcoal-on-Soft-White/Ivory meet AA (asserted from palette values, not a tool).
9. **⚪ Deployed on AdaLab under `/apps/<slug>/`.** Needs a tenant. The mechanism (frontend
   `basepath.ts` reading the prefixed browser URL under `stripped_prefix`) is verified in
   isolation for `/`, single- and nested-segment routes; card deploy is tenant-dependent.
10. **✅ `pytest` green.** **41 passed** on a fresh stamp (default and custom answers).

---

## 6. Addendum §A6 acceptance — results

11. **✅ Builds/runs on 8000; `.adalab` matches §A2 (`stripped_prefix: true`, `uid: 1`).**
    Container listens on 8000; `app.json` and `local_container_demo.json` were byte-checked
    against §A2 (stripped_prefix true, uid 1, port/test_serving_port 8000, `volume_mounts: []`,
    `maintainers: []`).
12. **✅ Missing/unwritable `DATA_DIR` fails loud, no silent fallback.** Verified live: a
    container with no volume prints the path + mount fix and exits ("Application startup
    failed"). `test_storage.py` pins missing/unwritable/never-created.
13. **✅ `lost+found` and `.AVI_SUCCESS` filtered wherever the app enumerates the volume.**
    `storage.list_volume_dir` filters them and is the one enumeration path
    (`GET /api/admin/exports`); `test_storage.py` + `test_export.py` confirm.
14. **✅ Redeploy simulation (new image tag, same mount).** Docker: build `:v1` → submit a
    group + result → destroy the container → build `:v2` (new tag) → run against the same
    `/asv-mnt/lab-data` mount → the group and result are intact. [CONFIRMED — see verification log]
15. **🟡 Router basepath resolves at runtime, no rebuild.** `resolveBasePath` verified for
    `/`, `/results`, `/apps/x/`, `/apps/x/results`, `/apps/x/admin/cohorts`. Full end-to-end
    under a real AdaLab prefix needs a tenant (⚪).
16. **✅ Three guardrail layers consistent.** `permissions.deny`, the hook's `PROTECTED`, and
    the `CLAUDE.md` protected-zone bullets are the identical 22-pattern set (script-checked).
17. **✅ README has the ASV runbook + single-replica constraint.** Create → ACL → mount in lab
    → `chown`/`chmod` → mount with Fast Mount; plus the single-replica warning and the
    Test → Build → Deploy order.

---

## 7. What I deliberately simplified

- **Charts** are a compact dependency-free inline-SVG bar chart (mean per cohort/group,
  current cohort Forest, prior Mint). Satisfies the compare view + §13 colour order; not a
  rich viz (no error bars/box plots).
- **"Migrations"** are `create_all` (idempotent) — the schema is chassis-fixed; a schema
  *field* changes the JSON payload, not the SQL tables.
- **No frontend unit tests** — the frontend is covered by type-check + build + the no-hex
  check + manual container verification; the schema→UI guarantee is tested on the backend.
- **Exports persist with stable filenames** (bounded, overwrite) so the atomic-write and
  volume-listing requirements are concrete and testable rather than vacuous.
- **`card.json`** is kept (base §12 + §A2 "remains unchanged"); its exact card-as-code fields
  are unverified against a tenant.

---

## 8. Weakest spots (where I'd look first)

1. **Anything needing a live AdaLab tenant is unverified**: the real `/apps/<slug>/` deploy
   (§15.9, §A6.15 end-to-end), the Gallery card deploy, and that the ASV + Fast Mount + chmod
   runbook is exactly right. I verified the *mechanisms* and matched the sibling-template
   conventions and AdaLab docs, but not tenant behaviour.
2. **The frontend chassis/seam guarantee is structural, not unit-tested.** `SchemaForm`
   handles the documented field patterns (number/int/enum/date/string/bool/optional), not
   arbitrary JSON Schema (arrays, nested objects, multi-branch unions). An exotic schema would
   render poorly rather than failing loudly.
3. **Dangerous-bash blocking is heuristic.** I modelled it on the addendum's description (no
   `protect_paths.py` to copy). It blocks the high-value cases (deleting the volume/DB, wiping
   a chassis tree, tampering with the guard) and errs toward not blocking to avoid false
   positives — so it is not an exhaustive shell sandbox.
4. **Brand contrast is asserted, not audited** with a WCAG tool, and the header title uses a
   §13-directed pair outside the six named ones (documented).
5. **`permissions.deny`/`ask` matching depends on the host Claude Code version's glob
   semantics.** The hook is the real enforcement and is verified; the lists are the advisory
   second layer.

---

## 9. What I'd do next with more time

- Deploy one stamped app to a real AdaLab tenant: close §15.9, §A6.15, the card deploy, and
  confirm the ASV/Fast Mount/chmod runbook and redeploy-survival on the actual platform.
- Add a **Vitest** frontend test that feeds `SchemaForm`/`basepath.ts` synthetic inputs, so
  the frontend half of the chassis/seam guarantee is a test, not a claim.
- Obtain the sibling's `protect_paths.py` and align the dangerous-bash rules exactly.
- Ship a **second worked seam** (e.g. a titration with a pH field) + a CI job that stamps and
  runs it, proving "define the schema, get the app" beyond the default example.
- Run a real Claude Code agent session in a stamped app for §15.7 (add a pH field / try to
  change group storage) to verify the *agent experience*, not just the hook mechanics.

---

## 10. Publishing note

The stamped app is turned into its own git repo by a copier `_task` (`git init -b main`).
The **template** itself is a plain directory (not git-initialised — I avoided a nested repo
in your tree, and commits are gated on your say-so). To publish: `git init` inside
`lab-exercise-app-template/`, commit, tag `v0.1.0`, push to `gh:cpdse/lab-exercise-app-template`.

**Placeholder assets:** the CPDSE logos in `frontend/src/assets/` and
`frontend/public/favicon.svg` are placeholders in the correct colourways. Replace with the
official CPDSE logo package before real use (also noted in the stamped app's README).
