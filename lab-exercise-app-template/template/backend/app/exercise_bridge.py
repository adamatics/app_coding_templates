"""The chassis's single point of contact with the exercise seam (CHASSIS).

Everything the chassis needs from ``exercise/`` goes through here: the JSON Schema (for
the form and API meta), payload validation, the ordered field names (for table/export
columns), and the optional ``analysis.summarize`` hook. Isolating the seam imports in one
module keeps the rest of the chassis exercise-agnostic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

import exercise
from exercise.schema import Measurement

__all__ = [
    "Measurement",
    "ValidationError",
    "json_schema",
    "field_names",
    "validate_payload",
    "run_exercise_analysis",
    "content_markdown",
]

_CONTENT_PATH = Path(exercise.__file__).parent / "content.md"


def json_schema() -> dict[str, Any]:
    """JSON Schema for one measurement (drives the form and /api/meta)."""
    return Measurement.model_json_schema()


def field_names() -> list[str]:
    """Ordered measurement field names — the stable export/table column order."""
    return list(Measurement.model_fields.keys())


def content_markdown() -> str:
    """The Home-page instructions from ``exercise/content.md`` (part of the seam)."""
    try:
        return _CONTENT_PATH.read_text(encoding="utf-8")
    except OSError:
        return "# Welcome\n\n(Instructions are in `exercise/content.md`.)"


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a submission and return a JSON-serialisable dict (dates -> strings).

    Raises ``pydantic.ValidationError`` on bad input; the router turns that into a 422.
    """
    model = Measurement.model_validate(payload)
    return model.model_dump(mode="json")


def run_exercise_analysis(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Call ``exercise.analysis.summarize`` if it exists, else return None.

    ``rows`` are the flattened latest-result dicts (schema fields + cohort + group).
    Any error in author-supplied analysis is caught and reported, never fatal.
    """
    try:
        from exercise import analysis  # optional — may be deleted by the author
    except Exception:  # pragma: no cover - seam may legitimately omit analysis
        return None
    summarize = getattr(analysis, "summarize", None)
    if summarize is None:
        return None
    try:
        import pandas as pd

        df = pd.DataFrame(rows)
        return summarize(df)
    except Exception as exc:  # author bug shouldn't take down the endpoint
        return {"error": f"exercise.analysis.summarize failed: {exc}"}
