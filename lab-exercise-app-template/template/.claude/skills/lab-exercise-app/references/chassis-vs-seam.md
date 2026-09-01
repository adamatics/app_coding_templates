# Chassis vs. seam (Streamlit architecture, Addendum B)

```
core/       framework-free Python — imports streamlit NOWHERE
ui/         thin Streamlit chassis UI
exercise/   THE SEAM (Python; may use streamlit)
app.py      entry point, course gate, onboarding, navigation
```

The UI package is `ui/`, never `pages/`: a directory called `pages/` beside `app.py` puts
Streamlit into magic multipage mode, turning every module in it into a URL-addressable page
outside the course gate. `tests/test_navigation.py` enforces the name.

## The seam (edit these)

| File | What it is |
| --- | --- |
| `exercise/schema.py` | The `Measurement` model. Framework-free (core imports it). Drives storage, CSV and export columns. |
| `exercise/capture.py` | The **data entry page**. `render_form(defaults)` returns a payload dict or `None`; optional `render_intro()` shows "what to enter here" above the form. Its header explains the contract — read it before editing. |
| `exercise/analysis.py` | The **analysis page**. `build_plots(own_df, compare_df, source)` returning `[{"title","figure","code"}]`, built with `core.plots` so every plot keeps its "Show the code" panel. Its header explains how to choose plots. |
| `exercise/content.md` | Instructions + the list under `## Analysis questions` (rendered with answer fields). |

## The chassis (editable — but shared)

`core/**`, `ui/**`, `app.py`, `assets/**`, the `Containerfile`, `pyproject.toml` and
`.streamlit/config.toml` are all editable. They are not per-app code: every app in the family
carries the same copy, so a change here is a change to the shared machinery. Prefer the seam
where it will do the job, keep the invariants below, and run the tests afterwards.

**Blocked (the hook exits 2):** `.adalab/app.json`, `.adalab/project.json`,
`.adalab/card.json` — deployment state that the AdaLab extension writes and fills in at deploy
time. Also commands that would delete the mounted volume, the SQLite database or `.adalab/`.

**Editable with confirmation:** `.adalab/local_container_1.json` (env vars, CPU/RAM, volume
mounts) and dependency-add commands.

## Invariants that survive a chassis edit

Each has a test; breaking one fails the suite.

| Invariant | Test |
| --- | --- |
| `core/` imports streamlit nowhere (nor does `exercise/schema.py`) | `tests/test_core_no_streamlit.py` |
| The UI package is `ui/`, never `pages/` | `tests/test_navigation.py` |
| Plots come from `core.plots`, so "Show the code" runs standalone | `tests/test_show_the_code.py` |
| No per-student data in module-level globals | `tests/test_concurrency.py` |
| `.adalab/` stays internally consistent | `tests/test_adalab_config.py` |

```
DATA_DIR=$(mktemp -d) python -m pytest -q
```

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
| Change identity, gate, cohorts, storage, export formats | `core/**` — chassis, so weigh it against the template first |

## Why it's built this way

CPDSE scientists will own eight or more of these apps for years, so the per-app surface is
Python they can maintain. Keeping the rest shared is what makes them a family: identical
identity, durability rules, visual identity and exports. That is a convention held by the
template and the tests, not a lock — the machinery is there to be maintained, and whoever
maintains it needs to be able to change it.

`core/` is framework-free because it is the seed of the shared library later apps will depend
on — a stray `import streamlit` there defeats that, and the test suite fails on it.

## Where a chassis change belongs

Ask one question: *would every app in the family want this?*

- **Yes** → make it in the **template repo**, so every app gets it and none drift. That is the
  path for anything about identity, durability, exports or the CPDSE visual identity.
- **No, it is genuinely specific to this course** → make it here. Nothing stops you. Note it in
  the app's README so the next person knows this app has diverged from the family.

The `ALLOW_DEPLOY_CONFIG_EDIT=1` env var lifts the remaining `.adalab` guard for template
maintainers.
