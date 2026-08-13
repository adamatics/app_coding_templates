"""Volume IO helpers (CHASSIS, framework-free). Addendum A §A3 / Addendum B §B6.

Every mounted AdaLab Shared Volume contains ``lost+found`` and ``.AVI_SUCCESS``; filter them
from any listing. Non-SQLite writes to the volume (the CSV mirror, exports) use
write-temp-then-``os.replace`` so a reader never sees a half-written file.
"""
from __future__ import annotations

import os
import threading
from itertools import count
from pathlib import Path

IGNORED_VOLUME_ENTRIES = {"lost+found", ".AVI_SUCCESS"}

# Temp-file names must be unique per *concurrent writer*, not just per process: a Streamlit
# app serves many sessions as threads in ONE process, so a PID-only name means 60 sessions
# fight over one temp file (found by the §B10 concurrency test).
_write_counter = count()


def list_volume_dir(path: Path) -> list[str]:
    """Names in ``path`` with the platform artifacts filtered out (§A6.13)."""
    if not path.is_dir():
        return []
    return sorted(n for n in os.listdir(path) if n not in IGNORED_VOLUME_ENTRIES)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` atomically: unique temp in the same dir, then replace.

    The temp name includes pid + thread id + a counter so concurrent sessions (threads in one
    Streamlit process) never share a temp file. ``os.replace`` is atomic on POSIX, so readers
    see either the old or the new file, never a torn one — and the last writer wins cleanly.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = f"{os.getpid()}-{threading.get_ident()}-{next(_write_counter)}"
    tmp = path.with_name(f".{path.name}.tmp-{unique}")
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))
