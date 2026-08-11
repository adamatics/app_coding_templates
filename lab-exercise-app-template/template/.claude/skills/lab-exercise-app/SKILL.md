---
name: lab-exercise-app
description: >
  Adapt this CPDSE lab-exercise app to a new or changed exercise. Use whenever the request
  is to add/remove/change a measurement field, change the entry form, add a chart or
  analysis, or edit the exercise instructions. Triggers: "add a field", "add a pH field",
  "change the measurement", "add a dropdown/date/notes field", "compute a statistic",
  "change the instructions", "adapt this app to <exercise>".
---

# Adapting a lab-exercise app

This app is one of a family stamped from a Copier template. Every app shares an identical
**chassis** and differs only in the **exercise seam**. Your job is almost always to edit the
seam and let the chassis follow.

## The one rule

**Edit only these three files:**

- `exercise/schema.py` — the `Measurement` Pydantic model (the single source of truth)
- `exercise/analysis.py` — optional `summarize(df)` for exercise-specific statistics
- `exercise/content.md` — the Home-page instructions

Everything else is chassis and is protected by a hook (`chassis_guard`) and by
`permissions.deny`. The entry form, the results table, the chart candidates and the export
columns are all **derived from `Measurement` at runtime**. Add a field to the schema and it
appears everywhere automatically — you do not (and must not) hand-edit the form, table,
charts, or export.

## Workflow for "add / change a field"

1. Open `exercise/schema.py`.
2. Add or edit a field on `Measurement`, giving it a type, a range (`ge`/`le` where it
   makes sense), a unit in the `description`, and marking it optional if appropriate.
3. That's it. Do not touch the frontend or backend. Confirm by running the app: the field
   shows up in **Enter results**, **Results**, the chart series list (if numeric), and the
   CSV/Parquet export.

Run `/new-exercise-field` to do this interactively.

## References

- `references/chassis-vs-seam.md` — the exact boundary and a "you want X → edit Y" map.
- `references/schema-cookbook.md` — field patterns (numeric+units, dropdowns, dates,
  replicates, free-text) and what makes a good example schema.
- `references/data-model.md` — cohort / append-only / supersede semantics. **Read this
  before doing anything with data**, so you never invent a parallel persistence path.

## What NOT to do

- Do not add student accounts, passwords, cookies, or a database server (see the app's
  non-goals). Identification is by group selection, on the honour system.
- Do not add a way to edit or delete results. Corrections **supersede**; resets **close a
  cohort**. Nothing is ever destroyed.
- Do not introduce colours outside `frontend/src/theme.css` or invent an error red/amber —
  the CPDSE palette has none. (You shouldn't be in the frontend at all.)
