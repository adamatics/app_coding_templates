"""Chassis analysis: anonymised distributions + summary stats (CHASSIS, no streamlit).

Comparison output is anonymised (§B4): no KUID or group labels, just distributions and
summary statistics. The exercise-specific visualisations live in ``exercise/analysis.py``.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from .exercise_bridge import numeric_field_names
from .results import columns, flat_rows


def to_dataframe(rows: list[dict[str, Any]], anonymise: bool = True) -> pd.DataFrame:
    """A DataFrame of results (schema fields + year/hold[/group/kuid]) for plotting/stats."""
    frame = pd.DataFrame(flat_rows(rows, anonymise=anonymise), columns=columns())
    for field in numeric_field_names():
        if field in frame.columns:
            frame[field] = pd.to_numeric(frame[field], errors="coerce")
    return frame


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Anonymised summary statistics over a set of results (no identity labels)."""
    frame = to_dataframe(rows, anonymise=True)
    stats: dict[str, Any] = {"n": int(len(frame))}
    per_field: dict[str, dict[str, float]] = {}
    for field in numeric_field_names():
        if field not in frame.columns:
            continue
        series = frame[field].dropna()
        if series.empty:
            continue
        per_field[field] = {
            "mean": round(float(series.mean()), 4),
            "std": round(float(series.std(ddof=1)), 4) if len(series) > 1 else 0.0,
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
            "n": int(len(series)),
        }
    stats["fields"] = per_field
    return stats
