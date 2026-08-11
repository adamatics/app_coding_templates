# Python style

- Target **Python 3.11** (the container runs `python:3.11-slim`). Avoid 3.12-only syntax.
- `from __future__ import annotations` at the top of modules; type-annotate public functions.
- Formatting is **ruff** (a PostToolUse hook runs `ruff format` automatically). Keep lines
  reasonable; don't fight the formatter.
- Prefer plain, explicit code over cleverness — students and teachers read this.
- Keep dependencies minimal (spec §2). Adding a runtime dependency touches `pyproject.toml`
  (an "ask" file) and must also work in the container build.
- In the **seam** (`exercise/`): `schema.py` is one Pydantic model named `Measurement`;
  `analysis.py`'s `summarize(df)` must be pure and defensive (it may get an empty DataFrame).
- Never add persistence outside the chassis model. Never add a path that deletes or mutates
  historical results — corrections supersede, resets close a cohort (see the data-model ref).
