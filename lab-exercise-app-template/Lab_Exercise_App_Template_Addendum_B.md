# ADDENDUM B: Streamlit switch and CPDSE design decisions

*Companion to `Lab_Exercise_App_Template_Spec.md` and Addendum A, issued 11 August 2026 after the CPDSE planning workshop. Where this conflicts with either earlier document, this wins. Addendum A's AdaLab and volume conventions remain in force except where B1 changes them.*

---

## B1. Framework switch: React out, Streamlit in

The React frontend is removed. The app is a **single-process, single-container Streamlit application**. Reason: CPDSE scientists, working with coding agents, will author and maintain eight or more of these apps for years. A Python-only exercise seam is something they can own; a TypeScript one is not.

**Deleted:** the entire `frontend/` tree, Vite, TanStack, `basepath.ts`, the Node build stage in the Containerfile, and every TypeScript guardrail rule.

**Retained unchanged from Addendum A:** port 8000, `Containerfile` naming, `.adalab/` contents, `stripped_prefix: true`, `uid: 1`, `.vscode` working mode, Test → Build → Deploy order, ASV persistence at `/asv-mnt/lab-data`, the chmod runbook, defensive volume IO with fail-loud startup, and the three-layer guardrail structure.

**Retained from the base spec:** append-only results with supersede, close-cohort-never-delete, fail-closed admin auth, export column stability across cohorts, the CPDSE visual identity in §13, and the chassis/seam separation as the central design idea.

### Architecture, non-negotiable

```
core/        framework-free Python. Imports streamlit NOWHERE.
             identity, storage, cohorts, export, admin logic, plot helpers.
pages/       thin Streamlit UI. Chassis pages only.
exercise/    THE SEAM. Python only, may use streamlit.
app.py       entry point, gate, navigation.
```

`core/` must be importable and testable with no Streamlit process running; a test asserting this is part of the suite. This keeps the UI swappable and, more importantly, makes `core/` the seed of the shared library that later apps will depend on.

### Verify before building far

Deploy a hello-world Streamlit app to the target AdaLab instance **first**, before any chassis work. Two things must be confirmed:

1. Streamlit's websocket connection survives AdaLab's app proxy.
2. Static assets resolve correctly under the app's URL prefix given `stripped_prefix: true`. If they do not, set `--server.baseUrlPath` and retest.

If either fails, stop and report; everything downstream depends on it.

## B2. Identity model

Four levels, all carried on every stored measurement so any view can filter at any level:

**Individual (KUID) → Group (2 to 3 students) → Hold (7 per year, class of ~200) → Year.**

Individual and group are the interaction layers. Hold and year exist for comparison and reporting. Which layers are active is configurable per app; an individual-only exercise has no group step.

**Course gate.** `COURSE_ID` and `COURSE_PASSWORD` from environment variables, rotated per semester at deploy time. `.adalab/app.json` sets `access_level: "public"`, since students have no AdaLab accounts and the gate is the control. This resolves the open access question from Addendum A.

**Self-registration after the gate.** Student enters KUID (three letters plus three digits, validated by format), display name, and hold, then joins an existing group or creates one. **No per-student passwords.** Identity is not encoded in the course password. Admin reassigns anyone afterwards.

Personal data note: KUID and names are stored and retained across years for cross-cohort comparison. This is covered by an existing KU data processing agreement, so no anonymisation at rest is required. Comparison **views** still display distributions without KUID or group labels, for pedagogical and fairness reasons rather than legal ones.

## B3. Page structure

Chassis pages, identical in every app: **Login gate · Register / My group · Data capture · Data analysis · FAQ · Admin.**

- **Data capture** hosts the exercise-specific input UI from `exercise/capture.py`. Values validated against `exercise/schema.py` on submit.
- **Data analysis** renders the teacher's questions from `exercise/content.md` as markdown with free-text answer fields stored alongside the measurements, plus the exercise-specific visualisations from `exercise/analysis.py`, plus the retrieval-scope control (B4) and the export block (B5).
- **FAQ** is markdown maintained by admins, so recurring questions get answered once.
- A **message banner** set by admin appears on every page when non-empty, for mid-session corrections ("use fridge C, A is broken").

## B4. Data retrieval and comparison

A scope selector on the analysis page: own, group, neighbouring group, hold, year, all years. The maximum permitted scope is set per app in course metadata by the teacher. Results from peers appear as they arrive; the UI states plainly that classmates working at a different pace may not have submitted yet, which is why students can return weeks later while writing their report.

Comparison output is anonymised: distributions and summary statistics, no KUID or group labels.

## B5. Export

Four outputs, all from `core/export.py`: **CSV**, **Excel**, **PDF report**, **HTML report**. The report combines the group's captured data, their free-text answers, and the plots from the analysis page into one document, because in organic chemistry the teacher approves it during the session and at least one teacher wants it emailed afterwards.

Assume students forget passwords and apps get retired. The export is what they keep.

## B6. Storage

**SQLite on the shared ASV as system of record, plus a long-format CSV mirror rewritten on every submission.** The CSV is readable and portable with no tooling; SQLite keeps concurrent writes safe. Both live under `DATA_DIR`.

One ASV is mounted into every course app so a KUID's history across apps and years is reachable. Each app owns its own SQLite file and CSV under a per-app subdirectory.

Course metadata table: course name, instructor, links to course material, downloadable documents, active message banner, permitted retrieval scope, FAQ content.

## B7. Plot helpers that emit their own source

In `core/plots.py`, plotting helpers return both the figure and the standalone code that reproduces it:

```python
def scatter(df, x, y, **kw) -> tuple[Figure, str]:
    """Returns (plotly figure, canonical pandas+plotly code that reproduces it)."""
```

The chassis renders an expandable **"Show the code"** panel under every plot containing `code_str`. The code shown must be plain pandas and plotly that a student could paste into a notebook, never Streamlit-specific code. Correct by construction, and it never drifts from what the app actually did.

This is a hard requirement, not a nice-to-have: these are pre-coding courses whose purpose includes exposing students to the code before they are asked to write it.

## B8. Stack

Python 3.11, uv, streamlit, pandas, plotly, lmfit, SQLite, and a PDF library of your choice that works headless in the container. R and Shiny are explicitly deferred; do not add abstraction now in anticipation of them.

## B9. Guardrails, revised paths

**Protected** (all three layers must agree): `core/**`, `pages/**`, `app.py`, `.adalab/app.json`, `.adalab/project.json`, `.vscode/**`, `Containerfile`, lockfiles, `.claude/hooks/**`, `.claude/settings.json`, secrets.

**Open, the seam:** `exercise/**` only.

The seam now includes UI code, which is intentional: with Streamlit, an exercise author writes Python for both capture and analysis. `.claude/rules/` loses the React rules and gains a rule stating that exercise pages compose chassis components from `core/` and `pages/_components.py` rather than styling from scratch, so the CPDSE identity holds across apps.

## B10. Acceptance criteria, replacing React-specific items

Base spec §15 item 9 and Addendum A item 15 are replaced by:

- Hello-world Streamlit app deploys on AdaLab and holds its websocket session under the URL prefix.
- `core/` imports and its tests pass with no Streamlit installed.
- Concurrency: 60 simultaneous sessions submitting results without error or cross-session state leakage. **Run this explicitly; the failure mode is a ruined first lesson with two classes in the lab at once.**
- Every plot in the reference app has a working "Show the code" panel whose code runs standalone against an exported CSV.
- Course gate rejects a wrong password, admits with the right one, and the app is reachable without an AdaLab account.
- Export produces all four formats; CSV columns are identical across two different cohorts of the same exercise.
