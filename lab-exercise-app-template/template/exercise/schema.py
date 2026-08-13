"""THE SEAM — measurement schema (framework-free: imported by core/, no streamlit).

Worked example: a chemistry **logP** workflow. For each compound a group records the value
from a public database, the value from an external prediction tool, their own measured value,
and a neighbouring group's measured value — so they can build a combined table and compare.

Replace with your own exercise. The chassis derives the CSV/export columns from these field
names, so keep names stable across years for cross-cohort comparison.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Measurement(BaseModel):
    """One logP record for one compound, by one student group."""

    compound_name: str = Field(min_length=1, max_length=64, description="Compound name, e.g. aspirin")
    database_logp: float = Field(ge=-5, le=12, description="logP from a public database (e.g. PubChem), unitless")
    tool_logp: float = Field(ge=-5, le=12, description="logP from an external prediction tool, unitless")
    measured_logp: float = Field(ge=-5, le=12, description="Your group's measured logP, unitless")
    neighbour_logp: float = Field(ge=-5, le=12, description="A neighbouring group's measured logP, unitless")
    method: Literal["shake-flask", "HPLC", "calculated"] = Field(
        description="How your group's value was obtained",
    )
    temperature_c: float = Field(ge=0, le=60, description="Temperature during measurement, °C")
    replicate: int = Field(ge=1, le=10, description="Replicate number for this compound")
    measured_on: date = Field(description="Date the measurement was taken")
    notes: Optional[str] = Field(default=None, max_length=500, description="Anything unusual (optional)")
