# Data model (read before touching data)

## Identity: four levels (§B2)

**Individual (KUID) → Group (2–3 students) → Hold (7 per year) → Year.** Every stored
measurement carries all four (via `member` → `group` → `cohort`), so any view can filter at
any level. Individual and group are the interaction layers; hold and year exist for
comparison and reporting. Which layers are active is configurable (`active_layers` setting) —
an individual-only exercise has no group step.

- **Course gate:** `COURSE_ID` + `COURSE_PASSWORD` env vars, rotated per semester at deploy.
  `access_level: "public"` in `.adalab/app.json` — students have no AdaLab accounts and the
  gate is the control.
- **Self-registration after the gate:** KUID (3 letters + 3 digits, format-validated),
  display name, hold, then join or create a group. **No per-student passwords.** A returning
  student is recognised by KUID — that's how they come back weeks later.
- KUID and names are stored and retained across years (covered by a KU data processing
  agreement). Comparison **views** are still anonymised — distributions only, no KUID or
  group labels.

## Entities

`cohort` (a Year; exactly one open) · `group` (unique name per year, carries `hold`) ·
`member` (KUID + display name) · `result` (JSON payload + `superseded_by` + `deleted_at`) ·
`answer` (free-text answers per group per question) · `setting` (course metadata) ·
`session_token` (durable browser sessions, no student passwords) · `event` (the log).

## Sessions and logging

- **`core/sessions.py`** — a student stays signed in across a refresh via an opaque random
  token in the URL, mapped to them by a `session_token` row (only its SHA-256 hash is stored).
  There are **no student passwords**; don't add any. Sign-out revokes; tokens expire.
- **`core/events.py`** — log anything meaningful with
  `events.log(session, "action", context=ctx, detail={...})` and errors with
  `events.log_error(session, "action", exc, context=ctx)`. Registrations, submissions,
  corrections, exports, admin actions and errors are already instrumented in `core/`; you
  rarely need to add more. Never log from an `st.download_button` builder — only from its
  `on_click` — or you record exports nobody took.

## The rules the code enforces (do not break)

1. **Append-only.** Students never edit or delete a result. A correction is a *new* row that
   supersedes the old one. Default queries are latest-only; exports can include full history
   with a `superseded` flag.
2. **Reset = close the year, never delete.** Writes to a closed year are rejected. Closed
   years stay fully queryable and exportable.
3. **Hard delete** is admin-only, one row, audited — for genuinely bogus rows.
4. **Storage is fail-loud.** `DATA_DIR` (default `/asv-mnt/lab-data`, a mounted AdaLab Shared
   Volume) must exist and be writable or the app refuses to start. Never "fix" a startup
   storage error by pointing `DATA_DIR` at a container-local path.
5. **SQLite is the system of record; a long-format CSV mirror is rewritten on every
   submission** (§B6). Both live under this app's subdirectory of the shared volume.
   `lost+found` and `.AVI_SUCCESS` are platform artifacts and are always filtered out.
6. **Single replica.** SQLite + WAL means one instance; never scale horizontally.

## Where it lives

`core/models.py` (tables), `core/results.py` (append-only + scopes + CSV mirror),
`core/identity.py` (KUID, gate, registration), `core/cohorts.py`, `core/admin.py`,
`core/export.py`. All framework-free — no streamlit.

## Consequence for you

If a request sounds like "let students fix/delete their entry", "wipe the data for the new
class", or "store results somewhere else" — translate it: supersede; close+open a year; use
the existing SQLite + CSV + exports. If it truly can't be expressed here, it's a
template-level change, not a per-app one.
