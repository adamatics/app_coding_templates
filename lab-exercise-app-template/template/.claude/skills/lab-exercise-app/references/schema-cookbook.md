# Schema cookbook

`exercise/schema.py` defines exactly one Pydantic v2 model named `Measurement`. Every field
becomes a form input, a table column, an export column, and — if numeric — a chart series.
Keep the model name `Measurement`.

## Field patterns

### Numeric with units and a range
Always put the unit in `description` and a sensible range in `ge`/`le`. The form shows the
unit as help text and enforces the range on both client and server.

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
demonstrates the form/table/chart/export before anyone customises it. The default absorbance
example does this.

## After you edit

Nothing else to do. Reload the app and check **Enter results** (new input), **Results**
(new column + chart candidate if numeric), and the CSV export (new column).
