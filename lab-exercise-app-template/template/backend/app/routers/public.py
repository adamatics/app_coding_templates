"""Public API — no authentication (spec §6). CHASSIS.

Identification model, stated plainly: **selecting your group from the dropdown IS the
identification.** Honour system by design — no accounts, no cookies for students.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..exercise_bridge import (
    Measurement,
    content_markdown,
    field_names,
    json_schema,
    run_exercise_analysis,
)
from .. import services

router = APIRouter(prefix="/api", tags=["public"])


# --- request bodies ---------------------------------------------------------
class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    members: list[str] = Field(default_factory=list)


class MemberAdd(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


def _numeric_fields(schema: dict[str, Any]) -> list[str]:
    """Chart candidates: measurement fields whose type is number/integer."""
    out: list[str] = []
    for name, spec in schema.get("properties", {}).items():
        types: set[Optional[str]] = {spec.get("type")}
        for sub in spec.get("anyOf", []):
            types.add(sub.get("type"))
        if types & {"number", "integer"}:
            out.append(name)
    return out


# --- meta -------------------------------------------------------------------
@router.get("/meta")
def get_meta(db: Session = Depends(get_db)) -> dict[str, Any]:
    schema = json_schema()
    open_cohort = services.get_open_cohort(db)
    return {
        "project_name": settings.project_name,
        "exercise_title": settings.exercise_title,
        "course_code": settings.course_code,
        "host_institution": settings.host_institution,
        "institution_name": settings.institution_name,
        "contact_email": settings.contact_email,
        "open_cohort": open_cohort.label if open_cohort else None,
        "admin_enabled": settings.admin_enabled,
        "demo_mode": settings.demo_mode,
        "schema": schema,
        "field_order": field_names(),
        "numeric_fields": _numeric_fields(schema),
    }


@router.get("/content")
def get_content() -> dict[str, str]:
    """Home-page instructions (Markdown) from the exercise seam."""
    return {"markdown": content_markdown()}


@router.get("/cohorts")
def get_cohorts(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """All cohorts (labels + counts) — powers the 'All years' selector on Results."""
    return services.list_cohorts(db)


# --- groups & members -------------------------------------------------------
@router.get("/groups")
def list_groups(
    cohort: Optional[str] = Query(default=None, description="cohort label; default = open cohort"),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    if cohort is None:
        open_cohort = services.get_open_cohort(db)
        if open_cohort is None:
            return []
        target = open_cohort
    else:
        target = services.get_cohort_by_label(db, cohort)
    return services.list_groups(db, target)


@router.post("/groups", status_code=201)
def create_group(body: GroupCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    group = services.create_group(db, body.name, body.members)
    return services.serialize_group(db, group)


@router.post("/groups/{group_id}/members", status_code=201)
def add_member(group_id: int, body: MemberAdd, db: Session = Depends(get_db)) -> dict[str, Any]:
    member = services.add_member(db, group_id, body.display_name)
    return {"id": member.id, "display_name": member.display_name, "group_id": group_id}


# --- results (append-only) --------------------------------------------------
@router.post("/groups/{group_id}/results", status_code=201)
def submit_result(group_id: int, measurement: Measurement, db: Session = Depends(get_db)) -> dict[str, Any]:
    payload = measurement.model_dump(mode="json")
    result = services.submit_result(db, group_id, payload)
    return {"id": result.id, "group_id": group_id, "values": payload, "superseded": False}


@router.post("/results/{result_id}/supersede", status_code=201)
def supersede_result(result_id: int, measurement: Measurement, db: Session = Depends(get_db)) -> dict[str, Any]:
    payload = measurement.model_dump(mode="json")
    new = services.supersede_result(db, result_id, payload)
    return {"id": new.id, "supersedes": result_id, "group_id": new.group_id, "values": payload}


@router.get("/results")
def get_results(
    cohort: str = Query(default="all", description="cohort label or 'all'"),
    latest: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return services.query_results(db, cohort=cohort, latest=latest)


# --- analysis ---------------------------------------------------------------
@router.get("/analysis")
def get_analysis(
    cohort: str = Query(default="all"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    chassis = services.chassis_summary(db, cohort=cohort)
    rows = services.query_results(db, cohort=cohort, latest=True)
    flat = [{**r["values"], "cohort": r["cohort"], "group": r["group"]} for r in rows]
    exercise_stats = run_exercise_analysis(flat)
    return {"cohort": cohort, "chassis": chassis, "exercise": exercise_stats}
