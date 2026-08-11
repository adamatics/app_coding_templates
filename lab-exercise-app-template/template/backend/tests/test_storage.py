"""Fail-loud storage: refuse to start on a missing/unwritable DATA_DIR (Addendum A §A3).

The failure mode this guards against — silently writing to container-local storage and
losing a year of data at the next redeploy — is the whole point, so these are load-bearing.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app import db, storage
from app.config import settings


def test_missing_data_dir_refuses_to_start():
    original = settings.data_dir
    object.__setattr__(settings, "data_dir", Path("/nonexistent-asv-mnt/lab-data-xyz"))
    try:
        with pytest.raises(db.StorageError) as exc:
            db.require_writable_data_dir()
        message = str(exc.value)
        # Names the path and points at the volume-mount fix — no silent fallback.
        assert "/nonexistent-asv-mnt/lab-data-xyz" in message
        assert "volume" in message.lower()
    finally:
        object.__setattr__(settings, "data_dir", original)


def test_data_dir_is_never_created(tmp_path):
    """require_writable_data_dir must NOT create DATA_DIR (that would be the silent fallback)."""
    missing = tmp_path / "not-mounted"
    original = settings.data_dir
    object.__setattr__(settings, "data_dir", missing)
    try:
        with pytest.raises(db.StorageError):
            db.require_writable_data_dir()
        assert not missing.exists()  # still absent — we refused, we didn't fabricate it
    finally:
        object.__setattr__(settings, "data_dir", original)


def test_list_volume_dir_filters_platform_artifacts(tmp_path):
    # A mounted AdaLab volume always contains these — they must never appear as app data.
    (tmp_path / "lost+found").mkdir()
    (tmp_path / ".AVI_SUCCESS").write_text("")
    (tmp_path / "results.sqlite").write_text("db")
    (tmp_path / "exports").mkdir()
    listed = storage.list_volume_dir(tmp_path)
    assert "lost+found" not in listed
    assert ".AVI_SUCCESS" not in listed
    assert set(listed) == {"results.sqlite", "exports"}


def test_atomic_write_leaves_no_temp_file(tmp_path):
    target = tmp_path / "sub" / "out.csv"
    storage.atomic_write_bytes(target, b"hello,world\n")
    assert target.read_bytes() == b"hello,world\n"
    # no leftover temp files in the directory
    assert [p.name for p in target.parent.iterdir()] == ["out.csv"]


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses filesystem permissions")
def test_unwritable_data_dir_refuses_to_start(tmp_path):
    readonly = tmp_path / "readonly"
    readonly.mkdir()
    readonly.chmod(0o500)
    original = settings.data_dir
    object.__setattr__(settings, "data_dir", readonly)
    try:
        with pytest.raises(db.StorageError) as exc:
            db.require_writable_data_dir()
        assert "not writable" in str(exc.value).lower()
    finally:
        object.__setattr__(settings, "data_dir", original)
        readonly.chmod(0o700)
