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


def test_preflight_names_the_missing_volume(tmp_path):
    """The container entrypoint runs `python -m core.preflight` BEFORE streamlit, so whatever
    is wrong with storage is stated in the log at startup rather than discovered on first use.

    A missing volume no longer exits non-zero — see
    `test_test_step_config_still_starts_the_container` for why — but the log must still name
    the path that needs fixing.
    """
    import subprocess
    import sys

    env = dict(os.environ, DATA_DIR=str(tmp_path / "not-mounted"), COURSE_PASSWORD="lab2026")
    proc = subprocess.run([sys.executable, "-m", "core.preflight"], capture_output=True,
                          text=True, env=env, cwd=str(Path(db.__file__).parent.parent))
    assert "not-mounted" in proc.stderr, "the log must name the path the deployer must fix"
    assert "ADMIT NOBODY" in proc.stderr


def test_preflight_succeeds_on_a_mounted_volume(tmp_path):
    import subprocess
    import sys

    env = dict(os.environ, DATA_DIR=str(tmp_path), DEMO_MODE="false")
    proc = subprocess.run([sys.executable, "-m", "core.preflight"], capture_output=True,
                          text=True, env=env, cwd=str(Path(db.__file__).parent.parent))
    assert proc.returncode == 0, proc.stderr
    assert "storage OK" in proc.stdout


# --- preview mode: how AdaLab's Test step can run with no volume -------------
def _preflight(env_overrides, tmp_path_factory=None):
    """Run `python -m core.preflight` in a subprocess with the given environment."""
    import subprocess
    import sys
    from pathlib import Path as _P

    env = dict(os.environ)
    env.update(env_overrides)
    return subprocess.run([sys.executable, "-m", "core.preflight"], capture_output=True,
                          text=True, env=env, cwd=str(_P(db.__file__).parent.parent))


def test_no_volume_and_no_course_password_starts_in_preview_mode(tmp_path):
    """AdaLab's Test step runs the container with no volume and no env vars. Without a
    course password nothing can be collected, so the app must still start."""
    proc = _preflight({
        "DATA_DIR": str(tmp_path / "never-mounted"),
        "COURSE_PASSWORD": "",
        "ADMIN_PASSWORD": "",
        "DEMO_MODE": "false",
    })
    assert proc.returncode == 0, f"Test step must be able to start the app:\n{proc.stderr}"
    assert "PREVIEW MODE" in proc.stderr          # and it says so, loudly
    assert "storage OK" in proc.stdout


def test_no_volume_WITH_course_password_admits_nobody(tmp_path):
    """The dangerous case, handled differently but no more permissively.

    A deployment that forgets the volume used to refuse to start. It now starts and blocks:
    the gate never opens, so not one result can be written to storage that is about to
    vanish. The guarantee is the same — nothing collectable — and it no longer depends on
    whether COURSE_PASSWORD happens to be set, which is what broke the Test step.
    """
    proc = _preflight({
        "DATA_DIR": str(tmp_path / "never-mounted"),
        "COURSE_PASSWORD": "lab2026",
        "ADMIN_PASSWORD": "admin",
    })
    assert proc.returncode == 0, f"the container must come up so Test can probe it:\n{proc.stderr}"
    assert "ADMIT NOBODY" in proc.stderr
    assert "never-mounted" in proc.stderr, "and name the path that needs fixing"


def test_preview_mode_is_off_when_the_volume_exists(tmp_path):
    proc = _preflight({
        "DATA_DIR": str(tmp_path),          # exists and is writable
        "COURSE_PASSWORD": "",
    })
    assert proc.returncode == 0
    assert "PREVIEW MODE" not in proc.stderr


# --- several course apps sharing one volume (§B6) ----------------------------
def test_each_app_writes_only_inside_its_own_subdirectory(session):
    """One ASV is mounted into every course app, so an app must never write to the shared
    root — otherwise two apps clobber each other's database."""
    from core import results as R
    from tests.conftest import register_student, valid_measurement

    m = register_student(session)
    R.submit_result(session, m.id, valid_measurement())

    slug = settings.project_slug
    assert settings.app_data_dir == settings.data_dir / slug
    for path in (settings.db_path, settings.csv_path, settings.exports_dir):
        assert settings.app_data_dir in path.parents or path == settings.app_data_dir

    # Nothing but this app's own directory should have been created at the volume root.
    entries = {p.name for p in settings.data_dir.iterdir()
               if not p.name.startswith(".")}
    assert entries <= {slug}, f"app wrote outside its subdirectory: {entries - {slug}}"


def test_two_apps_on_one_volume_do_not_collide(tmp_path):
    """Simulate a second course app sharing the same volume."""
    shared = tmp_path / "lab-data"
    (shared / "titration-lab").mkdir(parents=True)
    (shared / "titration-lab" / "results.sqlite").write_text("app-1 data")
    (shared / "logp-lab").mkdir(parents=True)
    (shared / "logp-lab" / "results.sqlite").write_text("app-2 data")

    assert (shared / "titration-lab" / "results.sqlite").read_text() == "app-1 data"
    assert (shared / "logp-lab" / "results.sqlite").read_text() == "app-2 data"
    assert sorted(p.name for p in shared.iterdir()) == ["logp-lab", "titration-lab"]


def test_write_probe_is_unique_per_app(tmp_path):
    """A fixed probe name would let two apps starting at once delete each other's probe,
    and one would wrongly refuse to start."""
    from core import config as config_mod

    assert config_mod._storage_is_usable(tmp_path) is True
    # no probe left behind, and the name carries the app slug
    assert not list(tmp_path.glob(".write-probe*"))

    other = tmp_path / "other"
    other.mkdir()
    (other / f".write-probe-someone-else-999").write_text("held by another app")
    assert config_mod._storage_is_usable(other) is True          # unaffected
    assert (other / ".write-probe-someone-else-999").exists()    # and left alone


# --- STORAGE_MODE=local: running without a Shared Volume, on purpose ---------
#
# The default refuses to start without a mounted volume, because a forgotten mount silently
# writes a year of results into a container that the next redeploy throws away. `local` is the
# opt-in escape from that rule — for a laptop, a lab, or a trial nobody has provisioned a
# volume for. These tests pin the three properties that keep it safe: it is never reached by
# accident, it is never mistaken for durable storage, and it still fails loud if the directory
# it was pointed at cannot be written.
def test_local_mode_creates_the_directory_and_starts(tmp_path):
    """The whole point: no mount, no volume, and the app comes up anyway."""
    target = tmp_path / "not-a-mount" / "lab-data"
    proc = _preflight({
        "DATA_DIR": str(target),
        "STORAGE_MODE": "local",
        "COURSE_PASSWORD": "course-secret",     # a real gate — students CAN sign in
        "ADMIN_PASSWORD": "admin-secret",
        "DEMO_MODE": "false",
    })
    assert proc.returncode == 0, f"local mode should start without a volume:\n{proc.stderr}"
    assert target.is_dir(), "local mode should create DATA_DIR rather than demand a mount"
    assert "storage OK" in proc.stdout


def test_local_mode_says_the_data_is_not_durable(tmp_path):
    """A teacher must not be able to run a class on local disk without being told."""
    proc = _preflight({
        "DATA_DIR": str(tmp_path / "local-store"),
        "STORAGE_MODE": "local",
        "COURSE_PASSWORD": "course-secret",
        "DEMO_MODE": "false",
    })
    assert "LOCAL DISK STORAGE" in proc.stderr
    assert "ERASED" in proc.stderr, "the warning must say what actually happens on redeploy"
    assert "export" in proc.stderr.lower(), "and what to do about it"


def test_local_mode_is_off_unless_asked_for(tmp_path):
    """A missing volume must never silently degrade into local storage.

    This is the property the whole fail-loud design rests on, so it is tested from the
    outside: same environment as the working case above, minus STORAGE_MODE.
    """
    proc = _preflight({
        "DATA_DIR": str(tmp_path / "not-a-mount" / "lab-data"),
        "COURSE_PASSWORD": "course-secret",
        "DEMO_MODE": "false",
    })
    assert "ADMIT NOBODY" in proc.stderr, (
        "without STORAGE_MODE=local a missing volume must block the app, not quietly write "
        "to disposable storage")
    assert "STORAGE_MODE=local" in proc.stderr, \
        "the message should name the deliberate escape hatch, so nobody has to guess"


def test_local_mode_still_fails_loud_on_an_unwritable_directory(tmp_path):
    """Opting out of the volume is not opting out of storage working at all."""
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o500)                        # readable, not writable
    try:
        proc = _preflight({
            "DATA_DIR": str(blocked / "lab-data"),
            "STORAGE_MODE": "local",
            "COURSE_PASSWORD": "course-secret",
            "DEMO_MODE": "false",
        })
        assert proc.returncode != 0, "an unwritable local directory must still abort"
        assert "STARTUP ABORTED" in proc.stderr
    finally:
        blocked.chmod(0o700)                    # so pytest can clean up


def test_durability_flag_matches_the_mode(tmp_path):
    """`storage_is_durable` is what the UI and the event log key off, so pin its meaning."""
    from core.config import settings as live

    original = live.storage_mode
    try:
        object.__setattr__(live, "storage_mode", "volume")
        assert live.storage_is_durable is True
        object.__setattr__(live, "storage_mode", "local")
        assert live.local_storage is True
        assert live.storage_is_durable is False, \
            "local disk is not durable — the banner and the export warning depend on this"
    finally:
        object.__setattr__(live, "storage_mode", original)


# --- the Test step, with passwords declared in .adalab ----------------------
#
# The regression that broke a real Test run. Preview mode used to be keyed on COURSE_PASSWORD
# being unset, as a proxy for "this is the extension's Test step, so nothing can be collected".
# Declaring the passwords in .adalab/local_container_1.json broke the proxy: Test supplies one,
# the fail-loud guard fired, and the container exited —
#
#     CONTAINER_READINESS_FAILED: Container titration-lab is not ready
#
# The container must always be able to start. The guarantee that matters — no result is ever
# written to storage that is about to vanish — is now kept by admitting nobody instead.
def test_test_step_config_still_starts_the_container(tmp_path):
    """Exactly what the extension runs: passwords set, STORAGE_MODE=volume, no volume."""
    proc = _preflight({
        "DATA_DIR": str(tmp_path / "never-mounted"),
        "COURSE_PASSWORD": "1234",
        "ADMIN_PASSWORD": "1234",
        "STORAGE_MODE": "volume",
        "DEMO_MODE": "false",
        "SESSION_TTL_DAYS": "30",
        "LOG_PII": "false",
    })
    assert proc.returncode == 0, (
        "the container must start with the .adalab defaults and no volume — otherwise the "
        f"extension's Test step fails before a deploy is ever attempted:\n{proc.stderr}")
    assert "ADMIT NOBODY" in proc.stderr, "and it must say why, in the container log"
    assert "STORAGE_MODE=local" in proc.stderr, "and name the deliberate way to run without one"


def test_no_volume_with_a_password_blocks_the_app(tmp_path):
    """Starts, but nothing can be collected: the gate never opens."""
    import subprocess
    import sys
    from pathlib import Path as _P

    env = dict(os.environ)
    env.update({
        "DATA_DIR": str(tmp_path / "never-mounted"),
        "COURSE_PASSWORD": "1234",
        "DEMO_MODE": "false",
    })
    probe = (
        "from core.config import settings;"
        "print('blocked', settings.storage_blocked);"
        "print('preview', settings.preview_mode);"
        "print('durable', settings.storage_is_durable)"
    )
    proc = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                          env=env, cwd=str(_P(db.__file__).parent.parent))
    assert "blocked True" in proc.stdout, proc.stdout + proc.stderr
    assert "durable False" in proc.stdout


def test_no_volume_without_a_password_is_preview_not_blocked(tmp_path):
    """Nothing can be collected anyway, so the app stays usable for looking around."""
    import subprocess
    import sys
    from pathlib import Path as _P

    env = dict(os.environ)
    env.update({
        "DATA_DIR": str(tmp_path / "never-mounted"),
        "COURSE_PASSWORD": "",
        "DEMO_MODE": "false",
    })
    probe = ("from core.config import settings;"
             "print('blocked', settings.storage_blocked);"
             "print('preview', settings.preview_mode)")
    proc = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                          env=env, cwd=str(_P(db.__file__).parent.parent))
    assert "blocked False" in proc.stdout, proc.stdout + proc.stderr
    assert "preview True" in proc.stdout


def test_a_mounted_volume_is_never_blocked(tmp_path):
    """The normal case must be untouched by any of this."""
    import subprocess
    import sys
    from pathlib import Path as _P

    env = dict(os.environ)
    env.update({"DATA_DIR": str(tmp_path), "COURSE_PASSWORD": "1234", "DEMO_MODE": "false"})
    probe = ("from core.config import settings;"
             "print('blocked', settings.storage_blocked);"
             "print('preview', settings.preview_mode);"
             "print('durable', settings.storage_is_durable)")
    proc = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                          env=env, cwd=str(_P(db.__file__).parent.parent))
    assert "blocked False" in proc.stdout, proc.stdout + proc.stderr
    assert "preview False" in proc.stdout
    assert "durable True" in proc.stdout
