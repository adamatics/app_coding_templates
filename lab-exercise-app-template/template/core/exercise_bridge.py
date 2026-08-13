"""The chassis's framework-free contact with the exercise seam (CHASSIS, no streamlit).

Only imports ``exercise.schema`` and reads ``exercise/content.md``. It deliberately does NOT
import ``exercise.capture`` or ``exercise.analysis`` (those use streamlit) — that keeps
``core/`` importable with no streamlit installed (§B1). Pages import the seam UI directly.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

import exercise
from exercise.schema import Measurement

from .errors import ValidationError

_CONTENT_PATH = Path(exercise.__file__).parent / "content.md"


def json_schema() -> dict[str, Any]:
    return Measurement.model_json_schema()


def field_names() -> list[str]:
    """Ordered measurement field names — the stable CSV/export column order."""
    return list(Measurement.model_fields.keys())


def numeric_field_names() -> list[str]:
    """Measurement fields whose JSON-Schema type is number/integer (chart candidates)."""
    out: list[str] = []
    for name, spec in json_schema().get("properties", {}).items():
        types = {spec.get("type")}
        for sub in spec.get("anyOf", []):
            types.add(sub.get("type"))
        if types & {"number", "integer"}:
            out.append(name)
    return out


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a submission; return a JSON-serialisable dict (dates -> strings)."""
    try:
        model = Measurement.model_validate(payload)
    except PydanticValidationError as exc:
        msgs = "; ".join(f"{e['loc'][0] if e['loc'] else '?'}: {e['msg']}" for e in exc.errors())
        raise ValidationError(msgs) from exc
    return model.model_dump(mode="json")


def content_markdown() -> str:
    try:
        return _CONTENT_PATH.read_text(encoding="utf-8")
    except OSError:
        return "# Instructions\n\n(see exercise/content.md)"


def content_sections() -> tuple[str, list[dict[str, str]]]:
    """Split content.md into (instructions markdown, analysis questions).

    Questions are the ordered list items under a ``## Analysis questions`` heading; each gets
    a stable key ``q1``, ``q2``, ... The chassis renders them with free-text answer fields
    stored alongside the measurements (§B3).
    """
    text = content_markdown()
    marker = re.search(r"^##\s+Analysis questions\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not marker:
        return text.strip(), []
    instructions = text[: marker.start()].strip()
    tail = text[marker.end():]
    # stop at the next H2 if present
    nxt = re.search(r"^##\s+", tail, re.MULTILINE)
    block = tail[: nxt.start()] if nxt else tail
    questions: list[dict[str, str]] = []
    for line in block.splitlines():
        m = re.match(r"^\s*(?:\d+\.|[-*])\s+(.*\S)\s*$", line)
        if m:
            questions.append({"id": f"q{len(questions) + 1}", "prompt": m.group(1).strip()})
    return instructions, questions
