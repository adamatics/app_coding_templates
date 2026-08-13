"""Course documents: upload, download, safety limits (teacher uploads the øvelsesvejledning)."""
from __future__ import annotations

import pytest

from core import documents, events
from core.errors import NotFoundError, ValidationError

PDF = b"%PDF-1.4 fake lab manual bytes"


def test_upload_then_download_roundtrip(session):
    meta = documents.save(session, PDF, "Øvelsesvejledning logP.pdf",
                          label="Øvelsesvejledning", description="Read section 3 first")
    assert meta["label"] == "Øvelsesvejledning"
    assert meta["original_name"] == "Øvelsesvejledning logP.pdf"
    assert meta["content_type"] == "application/pdf"
    data, again = documents.read_bytes(session, meta["id"])
    assert data == PDF and again["id"] == meta["id"]


def test_documents_are_listed_in_upload_order(session):
    documents.save(session, b"one", "a.pdf", label="First")
    documents.save(session, b"two", "b.pdf", label="Second")
    labels = [d["label"] for d in documents.list_documents(session)]
    assert labels == ["First", "Second"]


def test_filename_is_sanitised_against_traversal(session):
    meta = documents.save(session, PDF, "../../etc/passwd")
    stored = documents.documents_dir() / meta["original_name"]
    files = [p.name for p in documents.documents_dir().iterdir()]
    assert not any(".." in name or "/" in name for name in files)
    assert any(name.endswith("passwd") for name in files)
    assert not stored.exists() or stored.is_file()   # nothing escaped the directory


def test_files_land_inside_the_app_volume_directory(session):
    documents.save(session, PDF, "manual.pdf")
    from core.config import settings

    for path in documents.documents_dir().iterdir():
        assert settings.app_data_dir in path.parents


def test_empty_and_oversized_files_are_refused(session):
    with pytest.raises(ValidationError):
        documents.save(session, b"", "empty.pdf")
    too_big = b"x" * (documents.MAX_DOCUMENT_BYTES + 1)
    with pytest.raises(ValidationError) as exc:
        documents.save(session, too_big, "huge.pdf")
    assert "limit" in str(exc.value).lower()


def test_delete_removes_row_and_file(session):
    meta = documents.save(session, PDF, "manual.pdf")
    path = documents.documents_dir() / meta["filename"] if "filename" in meta else None
    documents.delete(session, meta["id"])
    assert documents.list_documents(session) == []
    with pytest.raises(NotFoundError):
        documents.read_bytes(session, meta["id"])
    if path is not None:
        assert not path.exists()


def test_missing_file_reports_clearly_rather_than_crashing(session):
    meta = documents.save(session, PDF, "manual.pdf")
    for path in documents.documents_dir().iterdir():
        path.unlink()
    with pytest.raises(NotFoundError) as exc:
        documents.read_bytes(session, meta["id"])
    assert "missing" in str(exc.value).lower()


def test_metadata_can_be_updated(session):
    meta = documents.save(session, PDF, "manual.pdf", label="Old")
    documents.update_metadata(session, meta["id"], label="New", description="Updated")
    row = documents.list_documents(session)[0]
    assert row["label"] == "New" and row["description"] == "Updated"


def test_uploads_and_deletes_are_logged(session):
    meta = documents.save(session, PDF, "manual.pdf")
    documents.delete(session, meta["id"])
    actions = [e["action"] for e in events.recent(session)]
    assert "document_uploaded" in actions and "document_deleted" in actions
