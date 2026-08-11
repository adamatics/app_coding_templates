"""Synthetic prior-cohort data for DEMO_MODE (spec §8, §15.6). CHASSIS.

Seeds two **closed** prior cohorts so the cross-year compare view has something to show
before any real class exists. The payloads are synthesised from the *current* JSON Schema
(not hard-coded for the worked example), so demo mode keeps working after an author changes
``exercise/schema.py``. Each cohort gets a small numeric shift so the multi-year chart shows
visible separation.

Idempotent: cohorts that already exist are left untouched.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .exercise_bridge import Measurement, json_schema
from .models import Cohort, Group, Member, Result

DEMO_COHORTS = ["2024-fall", "2025-fall"]
DEMO_GROUP_NAMES = ["Team Alpha", "Team Beta", "Team Gamma"]
DEMO_MEMBER_NAMES = ["Alex", "Bo", "Chris", "Dana", "Eli", "Fen"]


def _year_of(label: str, default: int = 2024) -> int:
    head = label.split("-")[0]
    return int(head) if head.isdigit() and len(head) == 4 else default


def _num(prop: dict[str, Any], rng: random.Random, shift: float) -> float:
    lo = prop.get("minimum", prop.get("exclusiveMinimum", 0.0))
    hi = prop.get("maximum", prop.get("exclusiveMaximum", lo + 10.0))
    if hi <= lo:
        hi = lo + 10.0
    span = hi - lo
    centre = lo + span * 0.5 + span * 0.15 * shift
    value = rng.gauss(centre, span * 0.12)
    return max(lo, min(hi, value))


def _value_for(name: str, prop: dict[str, Any], rng: random.Random, year: int, shift: float,
               replicate_counter: int) -> Any:
    # Resolve Optional[...] (anyOf with a null branch): use the non-null branch, ~always set.
    if "anyOf" in prop:
        non_null = [s for s in prop["anyOf"] if s.get("type") != "null"]
        if non_null:
            prop = {**non_null[0], **{k: v for k, v in prop.items() if k != "anyOf"}}

    if "enum" in prop:
        return rng.choice(prop["enum"])

    fmt = prop.get("format")
    ptype = prop.get("type")

    if fmt == "date":
        return date(year, rng.randint(9, 11), rng.randint(1, 28)).isoformat()
    if ptype == "integer":
        lo = int(prop.get("minimum", 1))
        hi = int(prop.get("maximum", lo + 5))
        if "replicate" in name and hi >= lo:
            return min(hi, lo + (replicate_counter % (hi - lo + 1)))
        return rng.randint(lo, max(lo, hi))
    if ptype == "number":
        return round(_num(prop, rng, shift), 4)
    if ptype == "boolean":
        return rng.random() > 0.5
    if ptype == "string":
        if "id" in name or "sample" in name:
            return f"S{rng.randint(1, 40)}"
        return f"demo {name}"
    # Fallback: leave to the model default if any.
    return None


def _synthesize(rng: random.Random, year: int, shift: float, replicate_counter: int) -> dict[str, Any]:
    schema = json_schema()
    props: dict[str, Any] = schema.get("properties", {})
    required = set(schema.get("required", []))
    payload: dict[str, Any] = {}
    for name, prop in props.items():
        # Optional fields: usually omit (None); required fields always filled.
        if name not in required and rng.random() > 0.25:
            continue
        value = _value_for(name, prop, rng, year, shift, replicate_counter)
        if value is not None:
            payload[name] = value
    # Validate/repair against the real model; on failure, drop optionals and retry.
    try:
        return Measurement.model_validate(payload).model_dump(mode="json")
    except Exception:
        strict = {k: payload[k] for k in required if k in payload}
        return Measurement.model_validate(strict).model_dump(mode="json")


def seed_demo_data(session: Session) -> list[str]:
    """Create the demo cohorts that don't already exist. Returns labels created."""
    created: list[str] = []
    for idx, label in enumerate(DEMO_COHORTS):
        exists = session.execute(
            select(Cohort.id).where(Cohort.label == label)
        ).first()
        if exists:
            continue
        year = _year_of(label)
        rng = random.Random(f"demo-{label}")  # deterministic per cohort
        shift = idx - 0.5  # spread the cohort means apart for a visible compare chart
        closed_at = datetime(year, 12, 15, tzinfo=timezone.utc)
        cohort = Cohort(label=label, status="closed",
                        created_at=datetime(year, 9, 1, tzinfo=timezone.utc),
                        closed_at=closed_at)
        session.add(cohort)
        session.flush()
        for gi, gname in enumerate(DEMO_GROUP_NAMES):
            group = Group(cohort_id=cohort.id, name=gname, name_key=gname.lower(),
                          created_at=cohort.created_at)
            session.add(group)
            session.flush()
            for mname in rng.sample(DEMO_MEMBER_NAMES, k=2):
                session.add(Member(group_id=group.id, display_name=mname,
                                    created_at=cohort.created_at))
            for r in range(rng.randint(4, 6)):
                payload = _synthesize(rng, year, shift + gi * 0.2, r + 1)
                session.add(Result(
                    group_id=group.id, payload=payload,
                    submitted_at=datetime(year, 10, rng.randint(1, 28), tzinfo=timezone.utc),
                ))
        created.append(label)
    session.commit()
    return created
