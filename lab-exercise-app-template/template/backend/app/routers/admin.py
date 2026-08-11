"""Admin API (spec §8) — every route guarded by the ``require_admin`` dependency,
except ``/login`` (which establishes the session) and ``/status`` (which reports whether
the admin area is enabled at all). CHASSIS.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import AdminGuard, clear_session, issue_session, verify_password
from ..config import settings
from ..db import get_db
from .. import services

router = APIRouter(prefix="/api/admin", tags=["admin"])


class LoginBody(BaseModel):
    password: str


class CohortCreate(BaseModel):
    label: str = Field(min_length=1, max_length=64)


class GroupRename(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class GroupMerge(BaseModel):
    source_id: int
    target_id: int


# --- auth -------------------------------------------------------------------
@router.get("/status")
def admin_status() -> dict[str, Any]:
    """Public: is the admin area enabled? (No secrets — just the on/off state.)"""
    return {"admin_enabled": settings.admin_enabled}


@router.post("/login")
def login(body: LoginBody, response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not settings.admin_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The admin area is disabled because ADMIN_PASSWORD is not set.",
        )
    if not verify_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password.",
        )
    issue_session(response)
    services.record_audit(db, "admin_login", {})
    db.commit()
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict[str, Any]:
    clear_session(response)
    return {"ok": True}


@router.get("/session", dependencies=[AdminGuard])
def session_ok() -> dict[str, Any]:
    return {"ok": True}


# --- cohort lifecycle -------------------------------------------------------
@router.get("/cohorts", dependencies=[AdminGuard])
def list_cohorts(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return services.list_cohorts(db)


@router.post("/cohorts", status_code=201, dependencies=[AdminGuard])
def open_cohort(body: CohortCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    cohort = services.create_cohort(db, body.label)
    return {"id": cohort.id, "label": cohort.label, "status": cohort.status}


@router.post("/cohorts/close", dependencies=[AdminGuard])
def close_cohort(db: Session = Depends(get_db)) -> dict[str, Any]:
    cohort = services.close_open_cohort(db)
    return {"id": cohort.id, "label": cohort.label, "status": cohort.status}


# --- group / member / result management (any cohort, all audited) -----------
@router.get("/groups", dependencies=[AdminGuard])
def admin_list_groups(cohort: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    target = services.get_cohort_by_label(db, cohort)
    return services.list_groups(db, target)


@router.patch("/groups/{group_id}", dependencies=[AdminGuard])
def rename_group(group_id: int, body: GroupRename, db: Session = Depends(get_db)) -> dict[str, Any]:
    group = services.rename_group(db, group_id, body.name)
    return services.serialize_group(db, group)


@router.post("/groups/merge", dependencies=[AdminGuard])
def merge_groups(body: GroupMerge, db: Session = Depends(get_db)) -> dict[str, Any]:
    target = services.merge_groups(db, body.source_id, body.target_id)
    return services.serialize_group(db, target)


@router.delete("/groups/{group_id}", dependencies=[AdminGuard])
def delete_group(group_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    services.delete_group(db, group_id)
    return {"ok": True}


@router.delete("/members/{member_id}", dependencies=[AdminGuard])
def delete_member(member_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    services.delete_member(db, member_id)
    return {"ok": True}


@router.delete("/results/{result_id}", dependencies=[AdminGuard])
def hard_delete_result(result_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    services.hard_delete_result(db, result_id)
    return {"ok": True}


@router.get("/audit", dependencies=[AdminGuard])
def audit_log(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return services.list_audit(db)


@router.get("/exports", dependencies=[AdminGuard])
def list_exports() -> list[dict[str, Any]]:
    """Export artifacts persisted on the volume. Uses the filtered listing so the AdaLab
    platform artifacts (lost+found, .AVI_SUCCESS) never appear (Addendum A §A6.13)."""
    from ..storage import list_volume_dir

    out: list[dict[str, Any]] = []
    for name in list_volume_dir(settings.exports_dir):
        path = settings.exports_dir / name
        if path.is_file():
            out.append({"name": name, "size": path.stat().st_size})
    return out


# --- demo data controls (only meaningful when DEMO_MODE=true) ---------------
@router.post("/demo/seed", dependencies=[AdminGuard])
def demo_seed(db: Session = Depends(get_db)) -> dict[str, Any]:
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo controls are only available when DEMO_MODE=true.",
        )
    from ..seed_demo import seed_demo_data

    created = seed_demo_data(db)
    services.record_audit(db, "demo_seed", {"created_cohorts": created})
    db.commit()
    return {"ok": True, "created_cohorts": created}
