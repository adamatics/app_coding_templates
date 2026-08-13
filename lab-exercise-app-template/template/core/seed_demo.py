"""Synthetic prior-year data for DEMO_MODE (CHASSIS, no streamlit).

Seeds two closed prior YEARS so the cross-year compare view has something to show before a
real class exists. Payloads are synthesised from the CURRENT JSON Schema, so demo mode keeps
working after an author changes ``exercise/schema.py``. Idempotent.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .exercise_bridge import Measurement, json_schema
from .models import Cohort, Group, Member, Result
from .results import rewrite_csv_mirror

DEMO_YEARS = ["2024", "2025"]


def _value_for(name: str, prop: dict[str, Any], rng: random.Random, year: int, shift: float) -> Any:
    if "anyOf" in prop:
        non_null = [s for s in prop["anyOf"] if s.get("type") != "null"]
        if non_null:
            prop = {**non_null[0], **{k: v for k, v in prop.items() if k != "anyOf"}}
    if "enum" in prop:
        return rng.choice(prop["enum"])
    fmt, ptype = prop.get("format"), prop.get("type")
    if fmt == "date":
        return date(year, rng.randint(9, 11), rng.randint(1, 28)).isoformat()
    if ptype == "integer":
        lo, hi = int(prop.get("minimum", 1)), int(prop.get("maximum", 6))
        return rng.randint(lo, max(lo, hi))
    if ptype == "number":
        lo = prop.get("minimum", prop.get("exclusiveMinimum", 0.0))
        hi = prop.get("maximum", prop.get("exclusiveMaximum", lo + 10.0))
        if hi <= lo:
            hi = lo + 10.0
        centre = lo + (hi - lo) * (0.5 + 0.15 * shift)
        return round(max(lo, min(hi, rng.gauss(centre, (hi - lo) * 0.12))), 4)
    if ptype == "boolean":
        return rng.random() > 0.5
    if ptype == "string":
        if "id" in name or "sample" in name or "compound" in name:
            return rng.choice(["aspirin", "caffeine", "ibuprofen", "paracetamol", "toluene"])
        return f"demo {name}"
    return None


def _synth(rng: random.Random, year: int, shift: float) -> dict[str, Any]:
    schema = json_schema()
    props, required = schema.get("properties", {}), set(schema.get("required", []))
    payload: dict[str, Any] = {}
    for name, prop in props.items():
        if name not in required and rng.random() > 0.3:
            continue
        val = _value_for(name, prop, rng, year, shift)
        if val is not None:
            payload[name] = val
    try:
        return Measurement.model_validate(payload).model_dump(mode="json")
    except Exception:
        strict = {k: payload[k] for k in required if k in payload}
        return Measurement.model_validate(strict).model_dump(mode="json")


def seed_demo_data(session: Session) -> list[str]:
    created: list[str] = []
    letters = "abcdefghijklmnopqrstuvwxyz"
    for idx, label in enumerate(DEMO_YEARS):
        if session.execute(select(Cohort.id).where(Cohort.label == label)).first():
            continue
        year = int(label)
        rng = random.Random(f"demo-{label}")
        created_at = datetime(year, 9, 1, tzinfo=timezone.utc)
        cohort = Cohort(label=label, status="closed", created_at=created_at,
                        closed_at=datetime(year, 12, 15, tzinfo=timezone.utc))
        session.add(cohort)
        session.flush()
        member_seq = 0   # per-cohort counter: KUIDs must be unique within a year
        for hold in (1, 2):
            for gi in range(2):
                name = f"H{hold}-Group {gi + 1}"
                group = Group(cohort_id=cohort.id, hold=hold, name=name, name_key=name.lower(),
                              created_at=created_at)
                session.add(group)
                session.flush()
                members = []
                for _ in range(rng.randint(2, 3)):
                    # Sequential suffix: guaranteed unique per cohort, which the
                    # uq_member_kuid_per_cohort constraint now requires.
                    kuid = "".join(rng.choice(letters) for _ in range(3)) + f"{member_seq:03d}"
                    member_seq += 1
                    m = Member(group_id=group.id, cohort_id=cohort.id, kuid=kuid,
                               kuid_key=kuid.lower(),
                               display_name=rng.choice(["Alex", "Bo", "Chris", "Dana", "Eli"]),
                               created_at=created_at)
                    session.add(m)
                    members.append(m)
                session.flush()
                for _ in range(rng.randint(3, 5)):
                    m = rng.choice(members)
                    session.add(Result(member_id=m.id, group_id=group.id,
                                       payload=_synth(rng, year, shift=idx - 0.5),
                                       submitted_at=datetime(year, 10, rng.randint(1, 28), tzinfo=timezone.utc)))
        created.append(label)
    session.commit()
    if created:
        rewrite_csv_mirror(session)
    return created
