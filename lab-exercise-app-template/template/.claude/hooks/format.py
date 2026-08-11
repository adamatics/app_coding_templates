#!/usr/bin/env python3
"""format — PostToolUse hook that auto-formats edited files (Addendum A §A4).

Runs ruff on Python and prettier on JS/TS/CSS/JSON after an edit. Best-effort: if the
formatter isn't installed it silently skips, and it never blocks the tool (always exit 0).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PY_EXT = {".py"}
JS_EXT = {".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".html"}


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return
    if event.get("tool_name") not in {"Edit", "Write", "MultiEdit"}:
        return
    tool_input = event.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not file_path:
        return
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".").resolve()
    target = Path(file_path)
    if not target.is_absolute():
        target = project / target
    if not target.is_file():
        return

    ext = target.suffix.lower()
    try:
        if ext in PY_EXT and shutil.which("ruff"):
            subprocess.run(["ruff", "format", str(target)], capture_output=True, timeout=30)
        elif ext in JS_EXT:
            prettier = project / "frontend" / "node_modules" / ".bin" / "prettier"
            if prettier.is_file():
                subprocess.run([str(prettier), "--write", str(target)], capture_output=True, timeout=30)
    except Exception:
        pass  # formatting must never break the workflow


if __name__ == "__main__":
    main()
