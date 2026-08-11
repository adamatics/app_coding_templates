"""CSV / Parquet export (spec §9). CHASSIS.

The export flattens each result's ``payload`` into columns **named exactly after the
schema fields**, followed by ``cohort``, ``group``, ``submitted_at`` and ``superseded``.
Because the column names come from the schema, exports from different years of the *same*
exercise are directly concatenable — the whole point of the statistics use case.

Access model:
* **Public:** latest-only **CSV** of any cohort (students pull data into their own analysis).
* **Admin only:** full history (``history=true``) and **Parquet** in any mode.
"""
from __future__ import annotations

import io
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from ..auth import is_admin
from ..config import settings
from ..db import get_db
from ..exercise_bridge import field_names
from ..storage import atomic_write_bytes
from .. import services

router = APIRouter(prefix="/api", tags=["export"])

# Meta columns always appended after the schema columns, in this fixed order.
META_COLUMNS = ["cohort", "group", "submitted_at", "superseded"]


def _rows_to_frame(rows: list[dict[str, Any]]):
    import pandas as pd

    columns = field_names() + META_COLUMNS
    records = []
    for r in rows:
        record = {name: r["values"].get(name) for name in field_names()}
        record["cohort"] = r["cohort"]
        record["group"] = r["group"]
        record["submitted_at"] = r["submitted_at"]
        record["superseded"] = r["superseded"]
        records.append(record)
    # Explicit columns keep the order stable even when there are zero rows.
    return pd.DataFrame.from_records(records, columns=columns)


@router.get("/export")
def export(
    request: Request,
    format: Literal["csv", "parquet"] = Query(default="csv"),
    cohort: str = Query(default="all", description="cohort label or 'all'"),
    history: bool = Query(default=False, description="include superseded rows"),
    db: Session = Depends(get_db),
) -> Response:
    admin = is_admin(request)
    # Gate: full history and Parquet are admin-only; latest-only CSV is public.
    if (history or format == "parquet") and not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Full-history and Parquet exports require an admin session. "
                   "Latest-only CSV export is open to everyone.",
        )

    rows = services.query_results(db, cohort=cohort, latest=not history)
    frame = _rows_to_frame(rows)

    scope = "full" if history else "latest"
    cohort_tag = cohort.replace("/", "-")
    base_name = f"{settings.project_slug}_{cohort_tag}_{scope}"

    if format == "parquet":
        buffer = io.BytesIO()
        frame.to_parquet(buffer, index=False)
        data = buffer.getvalue()
        media_type = "application/vnd.apache.parquet"
        filename = f"{base_name}.parquet"
    else:
        data = frame.to_csv(index=False).encode("utf-8")
        media_type = "text/csv; charset=utf-8"
        filename = f"{base_name}.csv"

    # Persist a copy to the volume atomically (Addendum A §A3). The filename is stable per
    # (format, cohort, scope), so this overwrites rather than accumulating — bounded and safe
    # to redo. A failed persist must never break the download the caller asked for.
    try:
        atomic_write_bytes(settings.exports_dir / filename, data)
    except OSError:
        pass

    if admin:
        services.record_audit(
            db, "export",
            {"format": format, "cohort": cohort, "history": history, "rows": len(rows)},
        )
        db.commit()

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
