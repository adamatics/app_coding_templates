"""THE SEAM — measurement schema for this exercise.

This is one of only three files you edit to change the exercise (the others are
``analysis.py`` and ``content.md``). Everything downstream follows from the model below:

    the entry form · client + server validation · the results table columns ·
    the chart candidates (numeric fields) · the export columns

So: define the fields here, get the app. You do **not** touch the chassis.

Rules for a good schema (see .claude/skills/lab-exercise-app/references/schema-cookbook.md):

* One Pydantic model named ``Measurement`` describing ONE result submission.
* Give every numeric field a unit in its ``description`` and a sensible ``ge``/``le`` range —
  the form turns these into help text and min/max validation.
* Use ``Literal[...]`` for categorical fields; the form renders a dropdown.
* Use ``date`` for calendar fields; the form renders a date picker.
* Optional free-text notes: ``str | None`` with ``default=None``.

The model below is a worked example (a spectrophotometric absorbance exercise) so the
stamped app runs end to end before you customise anything. Replace it with your own.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Measurement(BaseModel):
    """One absorbance reading recorded by a student group."""

    sample_id: str = Field(
        min_length=1,
        max_length=32,
        description="Your label for the sample, e.g. A1",
    )
    buffer: Literal["PBS", "Tris-HCl", "HEPES"] = Field(
        description="Buffer the sample was prepared in",
    )
    temperature_c: float = Field(
        ge=-50,
        le=150,
        description="Sample temperature, °C",
    )
    absorbance_au: float = Field(
        ge=0,
        le=4,
        description="Absorbance at 540 nm, AU",
    )
    dilution_factor: float = Field(
        ge=1,
        le=1000,
        description="Dilution factor applied before reading (1 = neat)",
    )
    replicate: int = Field(
        ge=1,
        le=10,
        description="Replicate number for this sample",
    )
    measured_on: date = Field(
        description="Date the reading was taken",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Anything unusual about this reading (optional)",
    )
