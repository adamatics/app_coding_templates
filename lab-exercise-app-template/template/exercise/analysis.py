"""THE SEAM — optional exercise-specific statistics.

If you export ``summarize(df)``, the chassis calls it and merges the result into
``GET /api/analysis`` alongside its own generic counts. ``df`` is a pandas DataFrame of
the **latest** results for the requested cohort scope, one row per submission, with one
column per field in ``schema.Measurement`` (plus ``cohort`` and ``group``).

Keep it pure and defensive: it may be called with an empty DataFrame (no results yet).
Return a flat dict of JSON-serialisable numbers/strings. Delete this function entirely if
your exercise needs no derived statistics — the chassis still works.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


def summarize(df: pd.DataFrame) -> dict[str, Any]:
    """Derived statistics for the absorbance worked example."""
    if df.empty or "absorbance_au" not in df.columns:
        return {"note": "No results yet."}

    absorbance = pd.to_numeric(df["absorbance_au"], errors="coerce").dropna()
    out: dict[str, Any] = {
        "n_readings": int(len(absorbance)),
        "mean_absorbance_au": round(float(absorbance.mean()), 4),
        "std_absorbance_au": round(float(absorbance.std(ddof=1)), 4) if len(absorbance) > 1 else 0.0,
        "min_absorbance_au": round(float(absorbance.min()), 4),
        "max_absorbance_au": round(float(absorbance.max()), 4),
    }
    if "temperature_c" in df.columns:
        temp = pd.to_numeric(df["temperature_c"], errors="coerce").dropna()
        if len(temp):
            out["mean_temperature_c"] = round(float(temp.mean()), 2)
    return out
