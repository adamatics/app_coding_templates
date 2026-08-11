#!/usr/bin/env python3
"""chassis_guard — PreToolUse hook, the REAL enforcement layer (Addendum A §A4).

One of three guardrail layers; the deny rules in ``settings.json`` and the "Protected zone"
in ``CLAUDE.md`` are best-effort and advisory, this hook is what actually blocks. The
``PROTECTED`` list below is the single source of truth and MUST stay identical to those two.

It does two jobs:
  1. blocks edits (Edit/Write/MultiEdit/NotebookEdit) to chassis files;
  2. blocks a few genuinely dangerous Bash commands (deleting the data volume or the SQLite
     DB, wiping a chassis tree, tampering with the guard).

Deliberately NOT blocked here (they are ``permissions.ask`` — editable with confirmation):
``frontend/src/theme.css`` and ``.adalab/local_container_demo.json``. The only always-writable
zone is the exercise seam (``exercise/``).

Blocking mechanism: exit code 2 with an explanatory message on stderr (Claude Code treats
this as "deny and show the reason to the model").

Escape hatch (template maintainers only, documented only in the TEMPLATE README):
``ALLOW_CHASSIS_EDIT=1`` disables the guard.
"""
import json
import os
import re
import sys
from pathlib import Path

# --- the canonical protected set (keep identical across all three guardrail layers) ---
PROTECTED = [
    "backend/app/**",
    "frontend/src/App.tsx",
    "frontend/src/main.tsx",
    "frontend/src/api.ts",
    "frontend/src/metaContext.ts",
    "frontend/src/global.d.ts",
    "frontend/src/ui.css",
    "frontend/src/lib/**",
    "frontend/src/components/**",
    "frontend/src/pages/**",
    "frontend/src/assets/**",
    "frontend/vite.config.ts",
    "frontend/tsconfig.json",
    "frontend/index.html",
    "frontend/scripts/**",
    ".adalab/app.json",
    ".adalab/project.json",
    ".adalab/card.json",
    ".vscode/**",
    "Containerfile",
    ".claude/settings.json",
    ".claude/hooks/**",
]

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def _matches(rel: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        base = pattern[:-3]
        return rel == base or rel.startswith(base + "/")
    return rel == pattern


def _is_protected(rel: str) -> bool:
    return any(_matches(rel, p) for p in PROTECTED)


def _edit_message(rel: str) -> str:
    return (
        f"\n⛔ chassis_guard: '{rel}' is a CHASSIS file and must not be edited per app.\n\n"
        "To change the exercise, edit ONLY the seam:\n"
        "  • exercise/schema.py    — the measurement fields\n"
        "  • exercise/analysis.py  — optional derived statistics\n"
        "  • exercise/content.md   — the Home-page instructions\n\n"
        "The entry form, results table, chart candidates and export columns are ALL derived\n"
        "from exercise/schema.py, so adding a field there updates every one of them\n"
        "automatically — you almost never need to touch the chassis.\n"
        "(theme.css and .adalab/local_container_demo.json are editable WITH confirmation.)\n"
        "See .claude/skills/lab-exercise-app/ for the chassis-vs-seam map.\n"
        "(Template maintainers editing the chassis itself: set ALLOW_CHASSIS_EDIT=1.)\n"
    )


# --- dangerous Bash guard ---------------------------------------------------
def _dangerous_bash(command: str) -> str | None:
    c = command
    # Never let a command destroy the persistent volume or the SQLite database.
    if re.search(r"\brm\b", c) and re.search(r"/asv-mnt|results\.sqlite|\.sqlite\b", c):
        return "This would delete student data on the persistent volume / SQLite database."
    # Recursive delete of a chassis or config tree.
    if re.search(r"\brm\b\s+-\S*r", c) and re.search(r"(?<![\w/])(backend|frontend|\.claude|\.adalab|\.vscode)\b", c):
        return "This would recursively delete a chassis/config directory."
    if re.search(r"\brm\b", c) and re.search(r"\bContainerfile\b", c):
        return "This would delete the Containerfile."
    # Tampering with the guard itself.
    if re.search(r"\b(rm|mv|chmod|chown|truncate)\b", c) and (".claude/hooks" in c or ".claude/settings.json" in c):
        return "This would tamper with the chassis guard."
    return None


def _bash_message(reason: str) -> str:
    return (
        f"\n⛔ chassis_guard: refusing this command.\n{reason}\n\n"
        "Data is durable by design: students never delete, corrections supersede, and "
        "'reset' closes a cohort. Nothing should destroy the volume, the database, or the "
        "chassis. If you genuinely mean to, do it manually outside the agent.\n"
    )


def main() -> None:
    if os.environ.get("ALLOW_CHASSIS_EDIT") == "1":
        sys.exit(0)
    try:
        event = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool = event.get("tool_name")
    tool_input = event.get("tool_input") or {}
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".").resolve()

    if tool in EDIT_TOOLS:
        file_path = tool_input.get("file_path") or tool_input.get("path") or tool_input.get("notebook_path")
        if not file_path:
            sys.exit(0)
        target = Path(file_path)
        if not target.is_absolute():
            target = project / target
        try:
            rel = str(target.resolve().relative_to(project)).replace(os.sep, "/")
        except Exception:
            sys.exit(0)
        if _is_protected(rel):
            sys.stderr.write(_edit_message(rel))
            sys.exit(2)
        sys.exit(0)

    if tool == "Bash":
        reason = _dangerous_bash(tool_input.get("command") or "")
        if reason:
            sys.stderr.write(_bash_message(reason))
            sys.exit(2)
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
