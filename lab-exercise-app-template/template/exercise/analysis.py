"""THE SEAM — the ANALYSIS page for this exercise. Edit this file for your course.

═══════════════════════════════════════════════════════════════════════════════
WHAT THIS FILE IS
═══════════════════════════════════════════════════════════════════════════════
The plots students see after they have entered data. You decide what is worth
looking at in *this* exercise; the app handles the rest of the page — the scope
selector (own / group / hold / year / all years), the summary table, your
questions from ``content.md``, and the export buttons.

Your job here is only:  take two DataFrames  →  return a list of plots.

═══════════════════════════════════════════════════════════════════════════════
THE RULE THAT MATTERS: BUILD PLOTS WITH ``core.plots``
═══════════════════════════════════════════════════════════════════════════════
Each helper returns **two** things:

    fig, code = plots.scatter(df, x="…", y="…")
                ↑     ↑
                │     └─ the plain pandas + plotly code that reproduces this plot
                └─ the figure students see

The app shows that code under every plot in a **"Show the code"** panel, and it
runs as-is in a notebook against the CSV the student exports. These are
pre-coding courses: seeing the code that made the picture is part of the teaching,
not decoration.

So do **not** build a plotly figure by hand here — students would silently lose
that panel. If you need a plot shape that ``core.plots`` doesn't have, ask for it
to be added to the chassis rather than working around it.

Available: ``scatter``, ``line``, ``histogram``, ``box``, ``bar`` — all take
``x=``, ``y=``, optional ``color=``, ``title=``.

═══════════════════════════════════════════════════════════════════════════════
THE TWO DATAFRAMES YOU ARE GIVEN
═══════════════════════════════════════════════════════════════════════════════
``own_df``      this student's group's data, with names — for "how did WE do?"
``compare_df``  the scope they picked, anonymised — for "how did we do
                COMPARED to everyone?" (no names or group labels, by design)

Both have one column per field in ``exercise/schema.py``, plus ``year``, ``hold``,
``group``, ``kuid``, ``submitted_at``, ``superseded``.

═══════════════════════════════════════════════════════════════════════════════
HOW TO CHOOSE PLOTS
═══════════════════════════════════════════════════════════════════════════════
Aim for three or four that each answer a question a student actually has:
  • "Does my measurement agree with the reference?"   → scatter measured vs reference
  • "Is the tool better than my hands?"               → scatter measured vs tool
  • "Am I an outlier?"                                → box/histogram over the class
  • "Has the class improved since last year?"         → box grouped by ``year``
Give every plot a title that states the question, and be defensive: this function
is called before anyone has entered anything, so check ``.empty`` first.

Everything below is a WORKED EXAMPLE (a logP exercise). Replace it with yours.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from core import plots


def build_plots(own_df: pd.DataFrame, compare_df: pd.DataFrame,
                source: str = "results.csv") -> list[dict[str, Any]]:
    """Return the plots for this exercise.

    Each item is ``{"title": str, "figure": fig, "code": code}`` — exactly what the
    ``core.plots`` helpers hand back. ``source`` is the name of the CSV the student can
    export; pass it through so the generated code reads the right file.
    """
    out: list[dict[str, Any]] = []

    # --- the group's own data ------------------------------------------------
    if not own_df.empty:
        fig, code = plots.scatter(
            own_df, x="database_logp", y="measured_logp", color="method",
            title="Does your measurement agree with the database?", source=source)
        out.append({"title": "Your measurement vs the database value", "figure": fig, "code": code})

        fig, code = plots.scatter(
            own_df, x="tool_logp", y="measured_logp", color="method",
            title="Does the prediction tool agree with your measurement?", source=source)
        out.append({"title": "Your measurement vs the tool prediction", "figure": fig, "code": code})

    # --- how the group compares (anonymised) --------------------------------
    if not compare_df.empty and "year" in compare_df.columns:
        fig, code = plots.box(
            compare_df, x="year", y="measured_logp",
            title="How is the class spread — and how does this year compare?", source=source)
        out.append({"title": "Class distribution by year", "figure": fig, "code": code})

    # --- ADD YOUR OWN BELOW --------------------------------------------------
    # e.g. a histogram of one field across the chosen scope:
    #
    # if not compare_df.empty:
    #     fig, code = plots.histogram(compare_df, x="measured_logp",
    #                                 title="Where does your value sit in the class?",
    #                                 source=source)
    #     out.append({"title": "Distribution of measured logP", "figure": fig, "code": code})

    return out
