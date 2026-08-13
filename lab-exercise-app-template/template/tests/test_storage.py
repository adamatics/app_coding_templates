"""Fail-loud storage + volume artifact filtering (§A3, §A6.12, §A6.13)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from core import db, storage
from core.config import settings


def test_missing_data_dir_refuses_to_start():
    original = settings.data_dir
    object.__setattr__(settings, "data_dir", Path("/nonexistent-asv-mnt/lab-data-xyz"))
    try:
        with pytest.raises(db.StorageError) as exc:
            db.require_writable_data_dir()
        msg = str(exc.value)
        assert "/nonexistent-asv-mnt/lab-data-xyz" in msg  # names the path
        assert "volume" in msg.lower()                     # points at the mount fix
    finally:
        object.__setattr__(settings, "data_dir", original)


def test_data_dir_is_never_created(tmp_path):
    """Creating DATA_DIR would be the silent container-local fallback we must never do."""
    missing = tmp_path / "not-mounted"
    original = settings.data_dir
    object.__setattr__(settings, "data_dir", missing)
    try:
        with pytest.raises(db.StorageError):
            db.require_writable_data_dir()
        assert not missing.exists()
    finally:
        object.__setattr__(settings, "data_dir", original)


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


def test_platform_artifacts_filtered(tmp_path):
    (tmp_path / "lost+found").mkdir()
    (tmp_path / ".AVI_SUCCESS").write_text("")
    (tmp_path / "results.sqlite").write_text("db")
    (tmp_path / "results.csv").write_text("a,b")
    listed = storage.list_volume_dir(tmp_path)
    assert "lost+found" not in listed and ".AVI_SUCCESS" not in listed
    assert set(listed) == {"results.sqlite", "results.csv"}


def test_atomic_write_leaves_no_temp(tmp_path):
    target = tmp_path / "sub" / "out.csv"
    storage.atomic_write_text(target, "x,y\n1,2\n")
    assert target.read_text() == "x,y\n1,2\n"
    assert [p.name for p in target.parent.iterdir()] == ["out.csv"]


def test_per_app_subdirectory_used(session):
    """Each app owns a subdirectory of the shared ASV (§B6)."""
    assert settings.app_data_dir == settings.data_dir / settings.project_slug
    assert settings.db_path.parent == settings.app_data_dir
    assert settings.csv_path.parent == settings.app_data_dir


def test_preflight_exits_nonzero_when_volume_missing(tmp_path):
    """The container entrypoint runs `python -m core.preflight` BEFORE streamlit, so a bad
    volume must exit non-zero. Otherwise Streamlit binds the port and serves an app whose
    writes all fail — the exact 'looks fine, loses a year of data' failure mode (§A3)."""
    import subprocess
    import sys

    env = dict(os.environ, DATA_DIR=str(tmp_path / "not-mounted"))
    proc = subprocess.run([sys.executable, "-m", "core.preflight"], capture_output=True,
                          text=True, env=env, cwd=str(Path(db.__file__).parent.parent))
    assert proc.returncode != 0, "preflight must fail when the volume is missing"
    assert "STARTUP ABORTED" in proc.stderr
    assert "not-mounted" in proc.stderr


def test_preflight_succeeds_on_a_mounted_volume(tmp_path):
    import subprocess
    import sys

    env = dict(os.environ, DATA_DIR=str(tmp_path), DEMO_MODE="false")
    proc = subprocess.run([sys.executable, "-m", "core.preflight"], capture_output=True,
                          text=True, env=env, cwd=str(Path(db.__file__).parent.parent))
    assert proc.returncode == 0, proc.stderr
    assert "storage OK" in proc.stdout
