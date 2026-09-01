#!/usr/bin/env python3
"""deploy_guard — PreToolUse hook guarding AdaLab deploy state and student data.

Deliberately narrow (see DECISIONS.md, "Guardrail relaxation"): **application code is not
protected**. Whoever stamps this template owns ``core/``, ``ui/``, ``app.py``, ``assets/``,
the ``Containerfile`` and the rest, and may edit any of it. What the architecture actually
depends on is enforced by the test suite rather than by a hook — see
``tests/test_core_no_streamlit.py``, ``tests/test_navigation.py``,
``tests/test_show_the_code.py`` and ``tests/test_concurrency.py``.

Two things are still blocked, because neither is part of developing an exercise and both are
expensive to get wrong:

  1. **AdaLab deployment state** (``PROTECTED``). ``.adalab/app.json``, ``project.json`` and
     ``card.json`` are written by the AdaLab extension and carry identifiers filled in at
     deploy time (``app_id``, ``metadata_id``, ``current_image_version``); hand-editing them
     is the documented cause of duplicate-container deploys and stale app state.
     ``.adalab/local_container_1.json`` is **not** blocked — it holds env vars, resources and
     volume mounts, which a developer legitimately sets. It sits at the ``permissions.ask``
     tier in ``settings.json`` instead.
  2. **Student data.** A command that would delete the mounted volume or the SQLite database
     destroys a cohort's results, which are append-only by design and have no undo.

``PROTECTED`` is the single source of truth for the blocked set and must stay identical to
``permissions.deny`` in ``.claude/settings.json`` and to the list in ``.claude/CLAUDE.md``.
``tests/test_guardrails.py`` fails if the three drift apart.

Blocking mechanism: exit code 2 with an explanatory message on stderr (Claude Code treats
this as "deny and show the reason to the model").

Escape hatch: ``ALLOW_DEPLOY_CONFIG_EDIT=1`` disables the guard entirely.
"""
import json
import os
import re
import sys
from pathlib import Path

# --- the canonical protected set (identical across all three layers) --------------------
PROTECTED = [
    ".adalab/app.json",
    ".adalab/project.json",
    ".adalab/card.json",
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
        f"\n⛔ deploy_guard: '{rel}' is AdaLab deployment state, not application code.\n\n"
        "These files are written by the AdaLab VS Code extension and carry identifiers filled\n"
        "in at deploy time (app_id, metadata_id, current_image_version). Hand-editing them is\n"
        "the documented cause of duplicate-container deploys and stale app state.\n\n"
        "  • env vars, CPU/RAM, volume mounts → .adalab/local_container_1.json\n"
        "    (editable, with confirmation)\n"
        "  • app name, URL, access level      → the AdaLab deploy wizard, then commit the\n"
        "    files it writes back\n\n"
        "Everything else in this app is yours to edit — core/, ui/, app.py and the seam.\n"
        "See .claude/skills/lab-exercise-app/references/adalab-deployment.md; "
        "tests/test_adalab_config.py\ncatches the mistakes that otherwise surface only at "
        "build or deploy time.\n"
        "(Template maintainers: ALLOW_DEPLOY_CONFIG_EDIT=1 lifts this guard.)\n"
    )


# --- dangerous Bash guard ---------------------------------------------------
def _dangerous_bash(command: str) -> str | None:
    c = command
    # Never let a command destroy the persistent volume or the SQLite database.
    if re.search(r"\brm\b", c) and re.search(r"/asv-mnt|results\.sqlite|\.sqlite\b", c):
        return "This would delete student data on the persistent volume / SQLite database."
    # Recursive delete of the deployment state.
    if re.search(r"\brm\b\s+-\S*r", c) and re.search(r"(?<![\w/])\.adalab\b", c):
        return "This would recursively delete .adalab/, the AdaLab deployment state."
    return None


def _bash_message(reason: str) -> str:
    return (
        f"\n⛔ deploy_guard: refusing this command.\n{reason}\n\n"
        "Data is durable by design: students never delete, corrections supersede, and "
        "'reset' closes a cohort. If you genuinely mean to, do it manually outside the "
        "agent.\n"
    )


def main() -> None:
    if os.environ.get("ALLOW_DEPLOY_CONFIG_EDIT") == "1":
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
