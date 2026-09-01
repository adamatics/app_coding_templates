---
paths:
  - "**/*.py"
---

# Python style

- Target **Python 3.11** (the container runs `python:3.11-slim`). Avoid 3.12-only syntax.
- `from __future__ import annotations` at the top of modules; type-annotate public functions.
- Formatting is **ruff** (a PostToolUse hook runs `ruff format` automatically).
- Prefer plain, explicit code over cleverness — scientists and teachers read and maintain this.
- Keep dependencies minimal (§B8: streamlit, pandas, plotly, lmfit, SQLite, a headless PDF
  lib). Adding a runtime dependency means editing `pyproject.toml` **and** confirming it
  builds in the container — an install command alone works locally and then breaks the image,
  which is why `pip/uv/poetry install|add` prompts for confirmation.

## The architectural rule that outranks style

**`core/**` must never import streamlit**, and neither must `exercise/schema.py` (because
`core` imports it). This keeps the UI swappable and makes `core/` the seed of the shared
library later apps will depend on. `tests/test_core_no_streamlit.py` fails the build on a
stray import — don't work around it, move the code to `ui/` or `exercise/` instead.

## In the seam (`exercise/`)

- `schema.py` — one Pydantic model named `Measurement`; framework-free.
- `capture.py` — `render_form(defaults) -> payload dict | None`. Gather values only; the
  chassis validates and stores them.
- `analysis.py` — `build_plots(own_df, compare_df, source) -> [{"title","figure","code"}]`,
  built with `core.plots` so each plot gets its "Show the code" panel. Be defensive: it may
  be called with empty DataFrames.

## Never

- Never add persistence outside `core/` (`core.results`, `core.identity`, `core.admin`).
- Never add a path that edits or deletes historical results — corrections supersede, resets
  close a year (see the data-model reference).
- Never add per-student passwords or accounts; the course password is the gate.
