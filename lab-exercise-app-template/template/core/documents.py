"""Course documents the teacher uploads for students to download (CHASSIS, no streamlit).

The lab manual (øvelsesvejledning), a data sheet, a worked example — the teacher uploads it
once in Admin and every student can download it from the app, instead of it living in an email
thread. Bytes are stored on the shared volume beside the database, so they survive redeploys
and are included in nothing but the volume itself (they are NOT in the SQLite backup — see
``README``).

Safety rules kept here rather than in the UI, so they hold no matter who calls:

* filenames are sanitised and stored under an id prefix — no path traversal, no collisions;
* a size ceiling (matching Streamlit's upload limit) so one big file can't fill the volume;
* writes are atomic (temp-then-replace), like every other volume write in this app;
* listing filters the AdaLab platform artifacts.
"""
from __future__ import annotations

import re
from datetime import timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import events
from .config import settings
from .errors import NotFoundError, ValidationError
from .models import Document
from .storage import atomic_write_bytes

# Matches .streamlit/config.toml's maxUploadSize (MB) so the UI and the rule agree.
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


def documents_dir() -> Path:
    return settings.app_data_dir / "documents"


def _safe_filename(name: str) -> str:
    """Strip any directory part and anything that isn't plainly a filename character."""
    base = Path(name or "").name                # drops ../ and absolute paths
    cleaned = _SAFE_NAME.sub("_", base).strip(" .")
    return cleaned[:120] or "document"


def _row(doc: Document) -> dict[str, Any]:
    uploaded = (doc.uploaded_at.replace(tzinfo=timezone.utc)
                if doc.uploaded_at and doc.uploaded_at.tzinfo is None else doc.uploaded_at)
    return {
        "id": doc.id, "label": doc.label or doc.original_name, "filename": doc.filename,
        "original_name": doc.original_name, "description": doc.description,
        "content_type": doc.content_type, "size_bytes": doc.size_bytes,
        "size_human": human_size(doc.size_bytes), "sort_order": doc.sort_order,
        "uploaded_at": uploaded.isoformat() if uploaded else None,
    }


def human_size(num: int) -> str:
    for unit in ("B", "kB", "MB"):
        if num < 1024 or unit == "MB":
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} MB"  # pragma: no cover


def save(session: Session, data: bytes, original_name: str, *, label: str = "",
         description: str = "", actor: str = "admin") -> dict[str, Any]:
    """Store an uploaded file and record it. Returns the metadata row."""
    if not data:
        raise ValidationError("That file is empty.")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ValidationError(
            f"That file is {human_size(len(data))}; the limit is "
            f"{human_size(MAX_DOCUMENT_BYTES)}. Link to it instead, or split it up.")

    safe = _safe_filename(original_name)
    highest = session.execute(
        select(Document.sort_order).order_by(Document.sort_order.desc()).limit(1)
    ).scalar()
    doc = Document(
        filename="pending", original_name=Path(original_name or safe).name, label=label.strip(),
        description=description.strip(), size_bytes=len(data),
        content_type=_guess_type(safe), sort_order=(highest or 0) + 1,
    )
    session.add(doc)
    session.flush()                       # need the id for the on-disk name
    doc.filename = f"{doc.id:04d}_{safe}"
    atomic_write_bytes(documents_dir() / doc.filename, data)
    session.commit()
    events.log(session, "document_uploaded", actor=actor,
               detail={"document_id": doc.id, "name": doc.original_name,
                       "size_bytes": doc.size_bytes})
    return _row(doc)


def _guess_type(filename: str) -> str:
    import mimetypes

    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def list_documents(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(Document).order_by(Document.sort_order, Document.id)
    ).scalars().all()
    return [_row(d) for d in rows]


def read_bytes(session: Session, document_id: int) -> tuple[bytes, dict[str, Any]]:
    doc = session.get(Document, document_id)
    if doc is None:
        raise NotFoundError("That document is no longer available.")
    path = documents_dir() / doc.filename
    if not path.is_file():
        raise NotFoundError(
            f"'{doc.original_name}' is recorded but its file is missing from the volume.")
    return path.read_bytes(), _row(doc)


def delete(session: Session, document_id: int, actor: str = "admin") -> None:
    """Remove a document. This deletes teaching material, never student data."""
    doc = session.get(Document, document_id)
    if doc is None:
        raise NotFoundError("That document no longer exists.")
    path = documents_dir() / doc.filename
    name = doc.original_name
    session.delete(doc)
    session.commit()
    try:
        path.unlink(missing_ok=True)
    except OSError:  # pragma: no cover - metadata is gone either way
        pass
    events.log(session, "document_deleted", actor=actor,
               detail={"document_id": document_id, "name": name})


def update_metadata(session: Session, document_id: int, *, label: Optional[str] = None,
                    description: Optional[str] = None, sort_order: Optional[int] = None,
                    actor: str = "admin") -> dict[str, Any]:
    doc = session.get(Document, document_id)
    if doc is None:
        raise NotFoundError("That document no longer exists.")
    if label is not None:
        doc.label = label.strip()
    if description is not None:
        doc.description = description.strip()
    if sort_order is not None:
        doc.sort_order = int(sort_order)
    session.commit()
    events.log(session, "document_updated", actor=actor, detail={"document_id": document_id})
    return _row(doc)
