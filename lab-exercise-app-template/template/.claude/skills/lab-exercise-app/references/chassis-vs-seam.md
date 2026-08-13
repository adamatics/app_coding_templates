# Chassis vs. seam (Streamlit architecture, Addendum B)

```
core/       framework-free Python — imports streamlit NOWHERE
pages/      thin Streamlit chassis UI
exercise/   THE SEAM (Python; may use streamlit)
app.py      entry point, course gate, navigation
```

## The seam (edit these)

| File | What it is |
| --- | --- |
| `exercise/schema.py` | The `Measurement` model. Framework-free (core imports it). Drives storage, CSV and export columns. |
| `exercise/capture.py` | The **data entry page**. `render_form(defaults)` returns a payload dict or `None`; optional `render_intro()` shows "what to enter here" above the form. Its header explains the contract — read it before editing. |
| `exercise/analysis.py` | The **analysis page**. `build_plots(own_df, compare_df, source)` returning `[{"title","figure","code"}]`, built with `core.plots` so every plot keeps its "Show the code" panel. Its header explains how to choose plots. |
| `exercise/content.md` | Instructions + the list under `## Analysis questions` (rendered with answer fields). |

## The chassis (do NOT edit — the guard blocks these)

`core/**`, `pages/**`, `app.py`, `.adalab/{app,project,card}.json`, `.vscode/**`,
`Containerfile`, lockfiles, `.claude/settings.json`, `.claude/hooks/**`.

**Editable with confirmation:** `.adalab/local_container_demo.json`, `pyproject.toml`,
`.streamlit/config.toml`, dependency-add commands.

## You want X → edit Y

| You want to… | Edit |
| --- | --- |
| Add / remove / rename a measurement field | `exercise/schema.py` |
| Change units, ranges, help text | `exercise/schema.py` (`Field(...)`) |
| Change what the input form looks like | `exercise/capture.py` |
| Add or change a plot | `exercise/analysis.py` (use `core.plots`) |
| Change instructions or questions | `exercise/content.md` |
| Change the CSV/export columns | **nothing** — they follow the schema |
| Change the "Show the code" panel | **nothing** — `core.plots` emits it |
| Change identity, gate, cohorts, storage, export formats | **nothing** — chassis |

## Why it's built this way

CPDSE scientists will own eight or more of these apps for years, so the per-app surface is
Python they can maintain. Everything else is frozen so the apps stay a family: identical
identity, durability rules, visual identity and exports.

`core/` is framework-free because it is the seed of the shared library later apps will depend
on — a stray `import streamlit` there defeats that, and the test suite fails on it.

## If you truly need a chassis change

That is a change to the **template**, not to a stamped app. Make it in the template repo
(where `ALLOW_CHASSIS_EDIT=1` lifts the guard) so every app benefits and none drift.
