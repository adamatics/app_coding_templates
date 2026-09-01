---
description: Add a measurement field to the exercise (schema + capture form; storage and exports follow)
---

Add a new field to this exercise. **Two files, both in the seam** — the chassis follows.

Do this:

1. Read `exercise/schema.py` and `exercise/capture.py` to see the current model and form.
2. Gather what the field needs (ask only for what's missing from the user's request):
   - **name** — snake_case, stable across years (it becomes the CSV/export column name)
   - **type** — number (`float`), whole number (`int`), text (`str`), choice (`Literal[...]`),
     date (`datetime.date`), or yes/no (`bool`)
   - **unit** — put it in the `description` (students are beginners; the label carries the unit)
   - **range** — `ge`/`le` for numbers, `min_length`/`max_length` for text, where sensible
   - **required or optional** — optional fields are `X | None = Field(default=None, ...)`
3. Add the field to `Measurement` in `exercise/schema.py`, following the patterns in
   `.claude/skills/lab-exercise-app/references/schema-cookbook.md`. Keep this file
   framework-free — it is imported by `core/`, which must never touch streamlit.
4. Add the matching input to `render_form` in `exercise/capture.py` and include it in the
   returned payload dict. Use the range as the input's `min_value`/`max_value` and the
   description as `help`, so the form mirrors the schema.
5. Tell the user it's done and that the field now flows automatically into:
   - the stored result and the long-format CSV mirror,
   - the results table and the comparison views,
   - all four exports (CSV, Excel, PDF report, HTML report),
   - the chart candidates (if numeric) — add a `core.plots` call in `exercise/analysis.py`
     if they want it plotted, which also gives it a "Show the code" panel.

Adding a field needs **no** chassis change: storage, the results table, the CSV mirror and all
four exports derive their columns from the schema. If you find yourself about to edit `core/`,
`ui/` or `app.py` for this, you have almost certainly missed a derivation — re-read
`.claude/skills/lab-exercise-app/references/chassis-vs-seam.md` first. (Those files are
editable; they are just not what a new field calls for.)

$ARGUMENTS
