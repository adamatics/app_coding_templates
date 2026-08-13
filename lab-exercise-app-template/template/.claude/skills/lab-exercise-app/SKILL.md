---
name: lab-exercise-app
description: >
  Adapt this CPDSE Streamlit lab-exercise app to a new or changed exercise. Use whenever the
  request is to add/remove/change a measurement field, change the capture form, add a plot or
  analysis, or edit the exercise instructions and questions. Triggers: "add a field", "add a
  pH field", "change the form", "add a plot", "compute a statistic", "change the instructions",
  "adapt this app to <exercise>".
---

# Adapting a lab-exercise app

This app is one of a family stamped from a Copier template. Every app shares an identical
**chassis** and differs only in the **exercise seam**. Your job is almost always to edit the
seam and let the chassis follow.

## The one rule

**Edit only `exercise/**`:**

- `exercise/schema.py` — the `Measurement` model (framework-free; `core/` imports it)
- `exercise/capture.py` — the Streamlit input UI for this exercise
- `exercise/analysis.py` — the exercise's plots, built with `core.plots`
- `exercise/content.md` — instructions and the `## Analysis questions` list

Everything else is chassis, protected by a hook and by `permissions.deny`. Storage, CSV/export
columns, identity, the course gate, cohorts, anonymised comparison and the four export formats
are all derived or provided — you do not rebuild them.

## Workflow: "add / change a field"

1. Edit `exercise/schema.py` (type, range, unit in the `description`, optional if appropriate).
2. Add the matching input to `exercise/capture.py` so students can enter it (return it in the
   payload dict; the chassis validates against the schema).
3. That's it. Storage, the results table, the CSV mirror and all four exports pick it up.

Run `/new-exercise-field` to do this interactively.

## Workflow: "add a plot"

Add it to `exercise/analysis.py` using a `core.plots` helper:

```python
fig, code = plots.scatter(own_df, x="database_logp", y="measured_logp", color="method",
                          title="Measured vs database", source=source)
out.append({"title": "Measured vs database", "figure": fig, "code": code})
```

The helper returns the figure **and** the standalone pandas+plotly code; the chassis renders
that in a "Show the code" panel. Never hand-build a plotly figure — students lose the panel,
which is a teaching requirement (§B7), and the test suite checks the code runs standalone.

## References

- `references/chassis-vs-seam.md` — the boundary and a "you want X → edit Y" map.
- `references/schema-cookbook.md` — field patterns and what makes a good schema.
- `references/data-model.md` — identity, cohort and supersede semantics. **Read before doing
  anything with data**, so you never invent a parallel persistence path.
- `references/adalab-deployment.md` — the `.adalab/` rules, the URL-prefix contract and the
  Shared Volume runbook. **Read before touching anything under `.adalab/` or deploying.**

## What NOT to do

- Do not import streamlit in `core/**` or `exercise/schema.py` (a test enforces this).
- Do not add per-student passwords or accounts; the course password is the gate.
- Do not add a way to edit or delete results. Corrections **supersede**; resets **close a
  year**. Nothing is ever destroyed.
- Do not use `st.error`/`st.success`/`st.warning` (off-palette) or hard-code hex colours;
  use `pages._components.notice` and `core.theme`.
