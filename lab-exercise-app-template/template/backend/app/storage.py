"""Volume IO helpers (Addendum A §A3). CHASSIS.

Two AdaLab-specific facts drive this module:

* Every mounted AdaLab Shared Volume contains ``lost+found`` and ``.AVI_SUCCESS`` — platform
  artifacts that are NOT app data and must be filtered out of any listing (§A6.13).
* The volume is a network mount that can be slow/absent, so every write to it **outside
  SQLite** goes through write-temp-then-``os.replace`` for atomicity (§A3): a reader never
  sees a half-written file, and a crash mid-write can't corrupt an existing one.
"""
from __future__ import annotations

import os
from pathlib import Path

# Platform artifacts present in every mounted volume — never app data.
IGNORED_VOLUME_ENTRIES = {"lost+found", ".AVI_SUCCESS"}


def list_volume_dir(path: Path) -> list[str]:
    """Names in ``path``, with the platform artifacts filtered out (§A6.13).

    Use this ANYWHERE the app enumerates volume contents, never a raw ``os.listdir``.
    """
    if not path.is_dir():
        return []
    return sorted(name for name in os.listdir(path) if name not in IGNORED_VOLUME_ENTRIES)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` atomically (temp file in the same dir, then replace).

    Same-directory temp keeps the final ``os.replace`` on one filesystem (atomic).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)  # atomic on POSIX
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
