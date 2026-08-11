# Data model (read before touching data)

The persistence design exists to make historical data **durable and comparable across
years**. Do not invent a parallel storage path; use what's here.

## Entities

- **cohort** — one class/year, labelled (e.g. `2026-fall`). Exactly one cohort is `open` at
  a time; the rest are `closed`. Closed cohorts are read-only but stay fully queryable and
  exportable forever.
- **group** — a student group within a cohort. Names are unique per cohort
  (case-insensitive). Picking a group from the dropdown IS the identification (honour
  system; no accounts, no passwords).
- **member** — a free-text name inside a group.
- **result** — one measurement submission (`payload` validated against
  `exercise.schema.Measurement`), with `submitted_at`, a nullable `superseded_by`, and a
  nullable admin-only `deleted_at`.
- **audit** — append-only log of admin actions.

## The rules the code enforces (and you must not break)

1. **Append-only.** Students never edit or delete a result. A correction is a *new* result
   that supersedes the old one (`superseded_by` on the old row). Default queries show
   latest-only; exports can include the full history with a `superseded` flag.
2. **Reset = close, never delete.** "Reset the app for a new class" means an admin *closes*
   the open cohort and *opens* a new one. There is **no code path that drops historical
   data.** Writes to a closed cohort are rejected (409).
3. **Hard delete is the only destructive op**, admin-only, one row at a time, and audited —
   for genuinely bogus rows.
4. **Storage is fail-loud.** `DATA_DIR` (default `/asv-mnt/lab-data`) must be a mounted,
   writable volume; the app refuses to start otherwise rather than silently writing to
   container-local storage. Never "fix" a startup storage error by pointing `DATA_DIR` at a
   container-local path.

## Where it lives

- Models: `backend/app/models.py` (chassis — don't edit).
- The durability rules: `backend/app/services.py` (chassis — the single home of these rules).
- The seam's only contract with persistence is the `Measurement` model. The chassis
  validates every submission against it and stores the JSON payload.

## Consequence for you

If a request sounds like "let students fix/delete their entry", "wipe the data for the new
class", or "store results in a spreadsheet/S3/another DB" — translate it into the model
above (supersede; close+open a cohort; use the existing SQLite + export). If it truly can't
be expressed here, it's a template-level change, not a per-app one.
