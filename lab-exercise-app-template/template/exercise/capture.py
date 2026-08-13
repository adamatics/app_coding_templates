"""THE SEAM — the DATA ENTRY page for this exercise. Edit this file for your course.

═══════════════════════════════════════════════════════════════════════════════
WHAT THIS FILE IS
═══════════════════════════════════════════════════════════════════════════════
This is the form students fill in at the bench. You own it; everything around it
(sign-in, groups, storage, corrections, exports) is handled by the app.

Your job here is only:  draw the inputs  →  return a dict of what the student typed.

The app then validates that dict against ``exercise/schema.py`` and stores it. If a
value is out of range or missing, the student gets a clear message and nothing is
saved — you do not have to check anything yourself.

═══════════════════════════════════════════════════════════════════════════════
THE TWO FILES THAT MUST AGREE
═══════════════════════════════════════════════════════════════════════════════
  exercise/schema.py   defines WHICH values exist, their type, range and unit
  exercise/capture.py  (this file) defines HOW the student types them in

Every key you return here must be a field in ``Measurement``. Add a field there,
add an input here. That is the whole loop.

═══════════════════════════════════════════════════════════════════════════════
HOW TO WRITE A GOOD ENTRY PAGE
═══════════════════════════════════════════════════════════════════════════════
* **Say what to enter, in lab language.** ``st.caption`` at the top: which sample,
  which instrument, what to do first. Students read this while holding a pipette.
* **Put the unit in the label** — "Temperature (°C)", not "Temperature".
* **Use the same ranges as the schema** as ``min_value``/``max_value``, so the
  student is stopped before they submit rather than after.
* **Use ``help=`` for the sentence you'd otherwise repeat 30 times.**
* **One reading per submission.** Three replicates = three submissions with
  replicate 1, 2, 3 — not three columns. That keeps the statistics simple.
* Group the fields the way the work happens (look-up values together, measured
  values together), with ``st.columns`` for tidy pairs.

Everything below is a WORKED EXAMPLE (a logP exercise). Replace the fields with
your own; keep the shape.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

import streamlit as st

# Must match the Literal[...] options in exercise/schema.py.
METHODS = ["shake-flask", "HPLC", "calculated"]


def render_intro() -> None:
    """Shown above the form. Tell the student what this page is for and what to have ready.

    Keep it short — three or four lines. Anything longer belongs in the exercise
    instructions (``exercise/content.md``) or in an uploaded document (Admin → Documents).
    """
    st.caption(
        "Record **one compound per submission**. Have ready: the database value, the value "
        "from the prediction tool, your own measurement, and the value from a neighbouring "
        "group. Enter each replicate as its own submission."
    )


def render_form(defaults: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    """Draw the inputs and return the student's values, or None if they haven't submitted.

    ``defaults`` is pre-filled when a student is CORRECTING an earlier reading — pass it as
    the ``value=`` of every input so they only have to change what was wrong.
    """
    d = defaults or {}

    with st.form("capture_form", clear_on_submit=False):
        # --- what was measured -------------------------------------------------
        compound = st.text_input(
            "Compound name", value=d.get("compound_name", ""),
            help="The name as written on your sample, e.g. aspirin.")

        # --- values looked up (before the bench) -------------------------------
        st.markdown("**Values you looked up**")
        c1, c2 = st.columns(2)
        database_logp = c1.number_input(
            "Database logP", value=float(d.get("database_logp", 0.0)),
            min_value=-5.0, max_value=12.0, step=0.01, format="%.2f",
            help="From a public database such as PubChem. Unitless.")
        tool_logp = c2.number_input(
            "Tool logP (prediction)", value=float(d.get("tool_logp", 0.0)),
            min_value=-5.0, max_value=12.0, step=0.01, format="%.2f",
            help="From the prediction tool named in the exercise instructions.")

        # --- values measured (at the bench) -----------------------------------
        st.markdown("**Values you measured**")
        c3, c4 = st.columns(2)
        measured_logp = c3.number_input(
            "Your measured logP", value=float(d.get("measured_logp", 0.0)),
            min_value=-5.0, max_value=12.0, step=0.01, format="%.2f",
            help="Your group's own result for this compound.")
        neighbour_logp = c4.number_input(
            "Neighbouring group's logP", value=float(d.get("neighbour_logp", 0.0)),
            min_value=-5.0, max_value=12.0, step=0.01, format="%.2f",
            help="Ask the group at the next bench for their value for the same compound.")

        # --- how and when ------------------------------------------------------
        st.markdown("**How the measurement was made**")
        method = st.selectbox(
            "Method", METHODS,
            index=METHODS.index(d["method"]) if d.get("method") in METHODS else 0,
            help="How your group obtained the measured value.")
        c5, c6 = st.columns(2)
        temperature_c = c5.number_input(
            "Temperature (°C)", value=float(d.get("temperature_c", 25.0)),
            min_value=0.0, max_value=60.0, step=0.5, format="%.1f",
            help="Room or bath temperature during the measurement.")
        replicate = c6.number_input(
            "Replicate number", value=int(d.get("replicate", 1)),
            min_value=1, max_value=10, step=1,
            help="1 for your first measurement of this compound, 2 for the second, and so on.")
        measured_on = st.date_input(
            "Date measured",
            value=date.fromisoformat(d["measured_on"]) if d.get("measured_on") else date.today())

        notes = st.text_area(
            "Notes (optional)", value=d.get("notes") or "",
            help="Anything unusual: cloudy sample, unstable reading, a step you had to repeat.")

        submitted = st.form_submit_button("Submit result")

    if not submitted:
        return None

    # Every key here MUST be a field name in exercise/schema.py.
    return {
        "compound_name": compound.strip(),
        "database_logp": database_logp,
        "tool_logp": tool_logp,
        "measured_logp": measured_logp,
        "neighbour_logp": neighbour_logp,
        "method": method,
        "temperature_c": temperature_c,
        "replicate": int(replicate),
        "measured_on": measured_on.isoformat(),
        "notes": notes.strip() or None,
    }
