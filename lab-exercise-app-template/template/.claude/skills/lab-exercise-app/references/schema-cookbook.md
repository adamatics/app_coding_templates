# Schema cookbook

`exercise/schema.py` defines exactly one Pydantic v2 model named `Measurement`. It is imported by framework-free `core/`, so it must never import streamlit. Every field
becomes a stored value, a table column, an export column, and — if numeric — a chart candidate.
Keep the model name `Measurement`.

## Field patterns

### Numeric with units and a range
Always put the unit in `description` and a sensible range in `ge`/`le`. Use them as the
input's help text and min/max in `exercise/capture.py`; the chassis re-validates on submit.

```python
temperature_c: float = Field(ge=-50, le=150, description="Sample temperature, °C")
absorbance_au: float = Field(ge=0, le=4, description="Absorbance at 540 nm, AU")
```

### Integer / replicate
```python
replicate: int = Field(ge=1, le=10, description="Replicate number for this sample")
```

### Categorical dropdown
Use `Literal[...]`; the form renders a `<select>`.

```python
from typing import Literal
buffer: Literal["PBS", "Tris-HCl", "HEPES"] = Field(description="Buffer used")
```

### Date
Use `datetime.date`; the form renders a date picker and the value stores as an ISO string.

```python
from datetime import date
measured_on: date = Field(description="Date the reading was taken")
```

### Short free text
```python
sample_id: str = Field(min_length=1, max_length=32, description="Your label, e.g. A1")
```

### Optional free-text notes (renders as a textarea)
```python
from typing import Optional
notes: Optional[str] = Field(default=None, max_length=500, description="Anything unusual (optional)")
```

## What makes a good schema

- **One row = one measurement.** If students take three replicates, that's three
  submissions with `replicate` 1/2/3 — not three columns.
- **Units in every numeric `description`.** Students are beginners; the label carries the unit.
- **Ranges that catch fat-finger errors** but don't reject legitimate values.
- **Stable field names across years.** Export columns are the field names, so keeping names
  stable is what lets you concatenate 2026 and 2027 data directly. Renaming a field breaks
  cross-year comparison — only do it deliberately.
- **Prefer `Literal` over free text** for anything with a fixed set of options: it keeps the
  data clean and gives students a dropdown.

## A good golden example

Ship the app with a schema that already exercises the common patterns (a numeric+unit field,
a dropdown, a replicate, a date, and an optional note), so a stamped app runs end to end and
demonstrates capture/table/plots/export before anyone customises it. The default logP
example does this.

## After you edit

Two steps, both in the seam:

1. `exercise/schema.py` — add the field (this drives storage, the CSV mirror and all exports).
2. `exercise/capture.py` — add the matching input to `render_form` and include it in the
   returned payload dict, so students can actually enter it. The chassis validates the payload
   against the schema before storing.

Nothing else to do: the results table, the CSV mirror, and the CSV/Excel/PDF/HTML exports all
follow the schema. If you want the new field plotted, add a `core.plots` call in
`exercise/analysis.py` (that also gives it a "Show the code" panel).
