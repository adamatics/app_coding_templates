# SPEC: `lab-exercise-app` — Copier template for student lab exercise apps

*Adamatics, August 2026. This document is the complete build instruction for Claude Code. The deliverable is a **Copier template repository**, not a single app. Every app stamped from it serves one lab exercise for an academic teaching group. Read the whole spec before writing code.*

---

## 1. What is being built and why

An academic group runs many lab exercises. Each exercise needs a small web app where student groups record their measurements. The apps must look and feel the same, persist results across years for statistical comparison, and differ only in the exercise-specific parts.

The template therefore has two strictly separated zones:

- **The chassis** (identical in every stamped app, never edited per app): branding and layout, menus, group and member self-service, cohort model, persistence, admin interface, export, deployment configuration.
- **The exercise seam** (the only per-app customization surface): the measurement schema, the results-entry form derived from it, and exercise-specific analysis or visualization.

This separation is enforced, not just documented: the template ships agent guidance (CLAUDE.md + a skill) and a guardrail hook that blocks edits to chassis files. The path of least resistance must be: define the schema, get the app.

## 2. Stack decisions (fixed, do not revisit)

- **Backend:** Python 3.12, FastAPI, uvicorn, SQLite (WAL mode), SQLAlchemy 2.x, Pydantic v2.
- **Frontend:** React 18 + Vite + TypeScript, built to static files and **served by FastAPI** from the same process. One container, one process, one port (8080). Streamlit was considered and rejected: it would mean a second server process in the container, a weaker admin/auth story, and per-app look-and-feel drift, which contradicts the entire purpose of the family.
- **Styling:** a design-token file implementing the CPDSE visual identity (§13), with Copier injecting only the per-app variables (exercise title, course code, accent choice). No component library beyond what keeps the bundle simple; keep dependencies minimal. The identity is chassis: apps in this family must be visually indistinguishable except for their content.
- **Persistence:** single SQLite file plus export artifacts under `DATA_DIR` (env var, default `/data`), which is expected to be a mounted persistent volume in deployment. The app must run correctly with an empty `DATA_DIR` (auto-migrate on start).
- **No user authentication for students.** Self-identification only. Admin area protected by a single password from an env var.

## 3. Template repository layout

```
lab-exercise-app-template/
├── copier.yml
├── README.md                        # template usage, not app README
└── template/
    ├── {{project_slug}}/
    │   ├── README.md.jinja          # app README; card description source
    │   ├── pyproject.toml.jinja
    │   ├── Containerfile            # single-stage-friendly, see §12
    │   ├── .adalab/
    │   │   ├── app.json.jinja
    │   │   └── card.json.jinja
    │   ├── .claude/
    │   │   ├── CLAUDE.md.jinja
    │   │   ├── settings.json        # hook registration
    │   │   ├── hooks/
    │   │   │   └── chassis_guard.py
    │   │   ├── commands/
    │   │   │   └── new-exercise-field.md
    │   │   └── skills/
    │   │       └── lab-exercise-app/
    │   │           ├── SKILL.md
    │   │           └── references/
    │   │               ├── chassis-vs-seam.md
    │   │               ├── schema-cookbook.md
    │   │               └── data-model.md
    │   ├── backend/
    │   │   ├── app/
    │   │   │   ├── main.py          # FastAPI app, static mount, startup migrate
    │   │   │   ├── config.py        # env parsing: DATA_DIR, ADMIN_PASSWORD, DEMO_MODE
    │   │   │   ├── db.py            # engine, session, migrations
    │   │   │   ├── models.py        # chassis ORM models (§5)
    │   │   │   ├── auth.py          # admin session auth (§8)
    │   │   │   ├── routers/
    │   │   │   │   ├── public.py    # cohort/groups/members/results endpoints
    │   │   │   │   ├── admin.py     # admin endpoints, guarded
    │   │   │   │   └── export.py    # CSV/Parquet export
    │   │   │   └── seed_demo.py     # synthetic prior-cohort data when DEMO_MODE=true
    │   │   └── tests/               # pytest: auth, cohort lifecycle, submit/supersede, export
    │   ├── exercise/                # THE SEAM — the only per-app code zone
    │   │   ├── __init__.py
    │   │   ├── schema.py            # Pydantic model of one measurement record
    │   │   ├── analysis.py          # optional derived stats per group/cohort
    │   │   └── content.md           # exercise instructions shown on Home
    │   └── frontend/
    │       ├── index.html, vite.config.ts, package.json, tsconfig.json
    │       └── src/
    │           ├── theme.css        # design tokens (Copier-injected)
    │           ├── App.tsx          # router + menu shell (chassis)
    │           ├── api.ts
    │           ├── pages/
    │           │   ├── Home.tsx             # renders exercise/content.md
    │           │   ├── Groups.tsx           # create/join group, member names
    │           │   ├── EnterResults.tsx     # form generated from schema (§10)
    │           │   ├── Results.tsx          # tables + charts, cohort compare
    │           │   └── admin/
    │           │       ├── AdminLogin.tsx
    │           │       ├── Cohorts.tsx
    │           │       ├── GroupsAdmin.tsx
    │           │       └── Export.tsx
    │           └── components/      # chassis widgets: SchemaForm, DataTable, Chart
    └── ...
```

## 4. Copier questions (`copier.yml`)

`project_name`, `project_slug` (derived), `exercise_title`, `course_code`, `host_institution` (choice: `SDU` | `UCPH` | `CPDSE`, controls the footer affiliation line only), `contact_email`, `default_cohort_label` (e.g. `2026-fall`), `app_port` (default 8080). Keep the list short; everything else is convention.

**No color or logo questions.** The CPDSE identity is fixed in the chassis (§13). Offering a color picker would produce exactly the drift the family exists to prevent.

## 5. Data model (chassis, SQLite)

- **cohort**: `id`, `label` (unique, e.g. `2026-fall`), `status` (`open` | `closed`), `created_at`, `closed_at`. Exactly one cohort may be `open` at a time.
- **group**: `id`, `cohort_id`, `name` (unique within cohort, case-insensitive), `created_at`.
- **member**: `id`, `group_id`, `display_name`, `created_at`. Free-text names entered by students.
- **result**: `id`, `group_id`, `payload` (JSON, validated against `exercise.schema` at submit time), `submitted_at`, `superseded_by` (nullable FK to result.id), `deleted_at` (nullable, admin only).
- **audit**: append-only log of admin actions (login, cohort close, deletes, exports).

Rules the code must enforce:

1. **Append-only results.** Students never edit or delete. A correction is a new submission that supersedes the old one (`superseded_by` set on the old row). Queries default to latest-only; exports include everything with a `superseded` flag.
2. **Reset means close, never delete.** "Resetting the app" for a new class = admin closes the open cohort and opens a new one. Closed cohorts become read-only and remain fully queryable and exportable. There is no code path that drops historical data. Hard delete exists only for individual bogus rows, admin-only, audited.
3. Writes to a closed cohort are rejected (409).
4. SQLite opened in WAL mode; classroom-scale concurrency (tens of simultaneous writers) must pass a test.

## 6. Public API (no auth)

`GET /api/meta` (exercise title, open cohort label, schema as JSON Schema) · `GET/POST /api/groups` (list open-cohort groups; create group with name + initial member names) · `POST /api/groups/{id}/members` (add member) · `POST /api/groups/{id}/results` (submit payload; validated) · `POST /api/results/{id}/supersede` (submit correction) · `GET /api/results?cohort=<label|all>&latest=true` (read across cohorts, powering the compare view) · `GET /api/analysis?cohort=...` (chassis summary stats merged with `exercise.analysis` output).

Identification model, stated plainly in code comments and UI copy: selecting a group from the dropdown **is** the identification. Honor system by design; no accounts, no cookies for students.

## 7. Student-facing frontend (chassis)

Menu: **Home · Groups · Enter results · Results · Admin** (admin entry visually de-emphasized).

- **Home:** exercise instructions from `exercise/content.md`.
- **Groups:** create a group (group name + member names, add/remove rows before save) or view existing groups and append yourself to one. No password, no lock.
- **Enter results:** select group from dropdown, fill the schema-generated form (§10), submit, get confirmation with the stored values echoed back.
- **Results:** table of latest results for the open cohort; chart panel; a cohort selector including `All years` so students can compare with previous cohorts and download CSV for their own statistical analysis.

## 8. Admin interface

- Entry: `/admin`, password form. Password compared constant-time against `ADMIN_PASSWORD` env var. On success, set a signed, HTTP-only session cookie (secret derived at startup; `itsdangerous` or equivalent). All `/api/admin/*` routes guarded by a FastAPI dependency. No password in the URL, no password stored on disk. Rotation = redeploy with a new env value; document this in the app README.
- If `ADMIN_PASSWORD` is unset, the admin area is disabled and the UI says so (fail closed, not open).
- Capabilities: cohort lifecycle (create label, close open cohort, see counts per cohort); group/member management within any cohort (rename, merge two groups, delete typo groups or members, hard-delete a result — all audited); export page (CSV and Parquet per cohort or all, latest-only or full history); demo-data controls when `DEMO_MODE=true`.

## 9. Exports and the statistics use case

`GET /api/export?format=csv|parquet&cohort=<label|all>&history=true|false`, admin-guarded for full history, public for latest-only CSV of any cohort (students must be able to pull data into their own analysis). Export flattens `payload` JSON into columns from the schema, plus `cohort`, `group`, `submitted_at`, `superseded`. Column names come from the schema field names, so exports from different years of the same exercise are directly concatenable.

## 10. The exercise seam contract

`exercise/schema.py` defines a single Pydantic model, `Measurement`, with typed, unit-annotated fields:

```python
class Measurement(BaseModel):
    """One result submission for this exercise."""
    temperature_c: float = Field(ge=-50, le=150, description="Sample temperature, °C")
    absorbance: float = Field(ge=0, description="Absorbance at 540 nm, AU")
    replicate: int = Field(ge=1, le=10, description="Replicate number")
```

The chassis consumes this model for validation, JSON Schema exposure, form generation (`SchemaForm` renders number/text/select/date inputs from JSON Schema, with units and ranges as help text and client-side validation mirroring server-side), table columns, chart candidates (numeric fields), and export columns. `exercise/analysis.py` may export `def summarize(df: pd.DataFrame) -> dict` for exercise-specific derived statistics; the chassis merges it into `/api/analysis`. `exercise/content.md` is the Home page. **Changing an exercise = editing these three files only.**

Ship the template with a worked example seam (a plausible titration or absorbance exercise) so a stamped app runs and demonstrates end to end before any customization.

## 11. Agent guidance assets (this is as important as the code)

- **CLAUDE.md (stamped into every app):** states the chassis/seam split in the first ten lines; lists chassis paths as do-not-edit; instructs that new fields, forms, charts, and analysis go through `exercise/`; points to the skill.
- **Skill `lab-exercise-app`:** when to use (any request to adapt the app to a new exercise, add fields, change analysis); `chassis-vs-seam.md` (the boundary, with a table of "you want X → edit Y" mappings); `schema-cookbook.md` (field patterns: numeric with units, categorical dropdowns, dates, replicates, free-text notes; what makes a good golden example); `data-model.md` (cohort/supersede semantics so the agent never invents its own persistence).
- **Hook `chassis_guard.py` (PreToolUse on Edit/Write):** blocks writes to `backend/app/**`, `frontend/src/components/**`, `frontend/src/App.tsx`, `.adalab/**`, `Containerfile`, exiting with a message that names the seam files instead. Escape hatch: `ALLOW_CHASSIS_EDIT=1` env var for template maintainers, mentioned only in the template README, not in the stamped app.
- **Command `/new-exercise-field`:** interactive helper that adds a field to `Measurement` with type, range, unit, and description, then reminds the agent that form, table, chart, and export update automatically.

## 12. Deployment and AdaLab integration

- **Containerfile:** stage 1 builds the frontend (`npm ci && npm run build`), stage 2 is the Python image copying the build into `backend/app/static/`; uvicorn serves API and static files on `$APP_PORT`. Must build and run with plain `podman build && podman run -p 8080:8080 -v ./data:/data -e ADMIN_PASSWORD=x`.
- **Env vars (the complete set):** `DATA_DIR` (default `/data`), `ADMIN_PASSWORD` (required for admin), `DEMO_MODE` (default `false`), `APP_PORT` (default 8080), `BASE_PATH` (default `/`, must support running under a sub-path since AdaLab serves apps at `/apps/<url>/`; both FastAPI root_path and the Vite base must honor it).
- **`.adalab/app.json`:** valid manifest for single-container deployment on the stamped values.
- **`.adalab/card.json`:** card spec per the Adamatics card-as-code convention: title from `exercise_title`, subtype `App`, keywords `teaching`, `lab-exercise`, plus course code and domain; description sourced from the app README. The README must follow the card copy standard: fixed headings (What it does / How to use it / Tech stack / Dependencies / Source / Access), **no Markdown tables anywhere in it** (card rendering does not support them; use labeled lines or fenced blocks), and end with a fenced YAML agent block:

```yaml
asset: app
owner: {{contact_email}}
version: 0.1.0
use: <deployed app URL>
source: <repo URL>
data: $DATA_DIR/results.sqlite (exports: /api/export)
```

- **Open deployment question, do not solve in code, surface in the README:** the persistence guarantee depends on `DATA_DIR` being a mounted volume that survives app redeploys on the target AdaLab tenant. Mark this as a deployment prerequisite and verify the mount mechanism with the platform team before first real use.

## 13. Visual identity (CPDSE)

The customer is the Center for Pharmaceutical Data Science Education (CPDSE), a cross-institutional center at SDU and UCPH. They publish a documented visual identity at https://cpdse.dk/visual-identity/, and these apps must look like they belong to it. All values below are from that page; do not invent alternatives.

**Palette.** Greens carry the scientific identity, golds add warmth, two neutrals handle text and surface.

- Forest Green `#3C5E3E` — primary dark. Headers, navigation band, dark sections.
- Sage Green `#5F7D61` — primary soft. Second-tier surfaces.
- Mint Gray `#A9BBAA` — primary light. Tags, dividers, quiet panels.
- Antique Gold `#D6C17C` — default accent. Buttons, key links, highlight glyphs.
- Warm Sand `#E4D7A1` — soft accent. Highlights, large colored surfaces.
- Ivory Gold Tint `#F6F1DC` — very light. Section bands, card fills.
- Charcoal Gray `#333333` — body text and high-contrast UI.
- Soft White `#F9F9F9` — main page background. **Never pure `#FFFFFF`.**

**Approved fill/ink pairs, the only combinations permitted for buttons, banners, and text on color:** Antique Gold on Forest Green · Warm Sand on Sage Green · Ivory Gold on Mint Gray · Forest Green on Antique Gold · Sage Green on Warm Sand · Mint Gray on Ivory Gold. Do not invent new pairings; they are contrast-tested.

**Typography.** Verdana for everything: headings, body, tables, captions. Weights 400 and 700 only. No italics in headings, no condensed widths, no display faces, no substitutes. Font stack: `Verdana, Geneva, "DejaVu Sans", sans-serif` (the fallbacks matter on Linux containers where Verdana is absent). Working scale: display 700, section heading 700, body 400, caption 400. Generous spacing is part of the identity, so set line-height around 1.6 for body and keep vertical rhythm loose.

**Logo.** Wide lock-up in the header, Antique Gold on Forest Green (the site default). Assets live in the published logo package as SVG; ship the SVG in `frontend/src/assets/` rather than hotlinking cpdse.dk. The snake-without-text mark may serve as favicon and loading glyph.

**Token file (`frontend/src/theme.css`), the single source for all of the above:**

```css
:root {
  --forest: #3C5E3E;  --sage: #5F7D61;   --mint: #A9BBAA;
  --gold: #D6C17C;    --sand: #E4D7A1;   --ivory: #F6F1DC;
  --charcoal: #333333; --soft-white: #F9F9F9;
  --font: Verdana, Geneva, "DejaVu Sans", sans-serif;
  --radius: 6px; --line: 1.6;
}
```

Every component reads these variables. No hex literals anywhere else in the frontend; add a lint rule or a CI grep that fails the build on a raw hex outside `theme.css`.

**Application to the chassis UI:**

- Header: Forest Green band, wide logo in Antique Gold, exercise title in Soft White.
- Page background Soft White; content cards Ivory Gold Tint fill with a Mint Gray hairline border.
- Primary buttons (Submit, Create group): Antique Gold fill, Forest Green ink. Secondary buttons: outlined Forest Green on Soft White. Destructive admin actions: Charcoal outline with an explicit confirm step, never a red the palette does not contain.
- Menu: active item marked with an Antique Gold underline, not a color swap.
- Tables: Mint Gray header row, Ivory Gold Tint zebra striping, Charcoal text.
- Form validation: helper text in Charcoal, error state as a Charcoal border plus explicit message text. The palette has no red or amber; do not add one. Convey state with words and weight, not invented colors.
- Charts: sequential series in the order Forest, Antique Gold, Sage, Mint, Warm Sand. For multi-year comparison, current cohort in Forest and prior cohorts in Mint Gray so the current class reads as foreground.
- Admin area: identical palette, distinguished by a Sage Green header band instead of Forest so an admin knows where they are without a second visual language.
- Accessibility: verify Charcoal on Ivory Gold Tint and on Soft White meet WCAG AA. If any approved pair fails at small sizes, use it for large text or surfaces only and note it in the app README; do not silently darken a brand color.

**Tone of UI copy:** plain, warm, non-jargon, matching the center's own voice ("A safe space to learn data science"). Students are beginners. Field labels carry units; error messages say what to do next.

## 14. Non-goals

No student accounts or SSO, no email, no gradebook, no LMS integration, no per-group passwords, no multi-exercise single deployment (one app = one exercise; the family pattern covers the rest), no database server, no admin password self-service UI.

## 15. Acceptance checklist

1. `copier copy` with defaults produces an app that builds its container and runs with an empty `DATA_DIR`.
2. Two browser sessions: create group A and group B, add members, submit results concurrently; both visible in Results.
3. Correction flow: supersede a result; Results shows latest; export with `history=true` shows both rows flagged.
4. Admin: wrong password rejected; correct password grants session; close cohort; student writes now rejected with a clear message; open new cohort; old cohort visible in the compare view and exportable.
5. Kill and restart the container with the same volume: all data intact.
6. `DEMO_MODE=true` seeds two synthetic prior cohorts; the cross-year compare chart renders.
7. Agent test: in a stamped app, ask Claude Code to "add a pH field with range 0 to 14". Outcome: only `exercise/schema.py` changes; form, table, chart, export pick it up. Then ask it to "change how groups are stored": the chassis guard blocks and points to the seam.
8. Brand check: no raw hex outside `theme.css` (CI grep passes); every button and banner uses an approved fill/ink pair; Verdana renders in the container with the declared fallbacks; contrast checked on Charcoal over Soft White and over Ivory Gold Tint.
9. Deployed on AdaLab under `/apps/<slug>/` with `BASE_PATH` set: navigation, API calls, and admin login all work under the sub-path; the Gallery card deploys from `card.json` with the README as description and the agent block intact.
10. `pytest` green: auth (constant-time compare, fail-closed when unset), cohort lifecycle, supersede semantics, unique group names per cohort, export column stability across cohorts.

## 16. Suggested build order for Claude Code

Chassis data layer and tests (§5) → public API (§6) → admin auth and API (§8) → frontend shell, theme.css and identity per §13, Groups and EnterResults with SchemaForm (§7, §10) → Results and compare view → export (§9) → demo seed → Containerfile and BASE_PATH behavior (§12) → agent guidance assets and hook (§11) → worked example seam → acceptance run (§15).
