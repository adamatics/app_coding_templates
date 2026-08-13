---
paths:
  - "exercise/**"
  - "pages/**"
  - "app.py"
---

# Exercise pages compose chassis components

Exercise pages **compose chassis components from `core/` and `pages/_components.py` rather
than styling from scratch**, so the CPDSE identity holds across every app in the family
(Addendum B §B9).

## Do

- Build plots with **`core.plots`** helpers (`scatter`, `line`, `histogram`, `box`, `bar`).
  They return `(figure, code_str)`; the chassis renders `code_str` in the "Show the code"
  panel. This is a teaching requirement — a hand-built figure silently loses it.
- Use **`pages._components`** for chrome: `notice(text, tone)` for messages,
  `show_the_code(fig, code)` for plots, `header`/`banner`/`footer` for layout.
- Keep colours in **`core.theme`** (the only module with hex). The plotly template and the
  CSS both read it.
- Return plain data from `exercise/capture.py` (`render_form` -> payload dict or `None`); the
  chassis validates against `exercise/schema.py` and stores it.

## Don't

- Don't call `st.error` / `st.success` / `st.warning` / `st.info` — they render off-palette
  red/green/amber. The CPDSE palette has none; use `_components.notice(..., "err"|"ok")` and
  convey state with words and weight (spec §13).
- Don't hard-code hex colours anywhere outside `core/theme.py`.
- Don't import streamlit from `core/**` or from `exercise/schema.py` (`core` imports the
  schema; a stray import breaks the framework-free guarantee and its test).
- Don't write to the database directly from a page; go through `core.results`,
  `core.identity`, `core.admin` so the append-only and cohort rules always apply.
- Don't build your own export; `core.export` produces all four formats (CSV, Excel, PDF, HTML).

## Streamlit session state

Streamlit state is per-session; never cache per-student data in a module-level global (that
leaks across sessions — a tested failure mode, §B10). Use `st.session_state` for the current
student, and `@st.cache_resource` only for process-wide setup like the DB bootstrap.
