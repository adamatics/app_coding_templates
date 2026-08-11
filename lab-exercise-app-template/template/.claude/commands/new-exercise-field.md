---
description: Add a field to the exercise Measurement schema (form, table, chart, export follow automatically)
---

Add a new field to `exercise/schema.py` — the ONLY change needed to add a measurement.

Do this:

1. Read `exercise/schema.py` to see the current `Measurement` model and its style.
2. Gather what the field needs (ask the user only for what's missing from their request):
   - **name** — snake_case, stable across years (it becomes the export column name)
   - **type** — number (`float`), whole number (`int`), text (`str`), choice
     (`Literal[...]`), date (`datetime.date`), or yes/no (`bool`)
   - **unit** — put it in the `description` (students are beginners; the label carries the unit)
   - **range** — `ge`/`le` for numbers, `min_length`/`max_length` for text, where sensible
   - **required or optional** — optional fields are `X | None = Field(default=None, ...)`
3. Add the field to `Measurement` following the patterns in
   `.claude/skills/lab-exercise-app/references/schema-cookbook.md`. Edit **only**
   `exercise/schema.py`.
4. Tell the user it's done and that the field now appears automatically in:
   - the **Enter results** form (with its unit and range as help text),
   - the **Results** table,
   - the **chart** series list (if the field is numeric),
   - the **CSV/Parquet export** (as a new column named exactly after the field).

Do **not** edit the form, table, chart, backend, or export — they are chassis and are
derived from the schema. If you find yourself wanting to, re-read
`.claude/skills/lab-exercise-app/references/chassis-vs-seam.md`.

$ARGUMENTS
