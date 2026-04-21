#!/usr/bin/env -S uv run --script
# /// script
# dependencies = []
# ///
"""PreToolUse hook: blocks edits to protected paths and dangerous bash.

Exit 2 blocks the tool call and feeds stderr back to Claude as guidance.
Exit 0 allows it. Exit 1 does NOT block (common footgun); avoid.
"""

import json
import os
import re
import sys

PROTECTED_PATHS = [
    # Backend infrastructure
    r"^app/core/",
    r"^app/api/main\.py$",
    r"^app/api/deps\.py$",
    r"^app/models/base\.py$",
    r"^main\.py$",
    # Frontend infrastructure
    r"^frontend/src/lib/basepath\.ts$",
    r"^frontend/src/styles/tokens\.css$",
    r"^frontend/src/api/client\.ts$",
    r"^frontend/src/main\.tsx$",
    r"^frontend/vite\.config\.ts$",
    r"^frontend/package\.json$",
    r"^frontend/pnpm-lock\.yaml$",
    # Platform and build
    r"^\.adalab/",
    r"^\.vscode/",
    r"^Containerfile$",
    r"^requirements\.txt$",
    r"^pyproject\.toml$",
    r"^uv\.lock$",
    # Claude Code config itself
    r"^\.claude/hooks/",
    r"^\.claude/settings\.json$",
    # Secrets
    r"^\.env(\.|$)",
    r"\.pem$",
    r"\.key$",
]

DANGEROUS_BASH = [
    (r"\brm\s+-[a-z]*r[a-z]*f", "rm -rf variants are blocked"),
    (r"\bcurl\b[^|]*\|\s*(sh|bash)", "curl | shell is blocked"),
    (r"\bgit\s+push\b", "git push is blocked; human will push"),
    (r"\b(uv|pip)\s+add\s+", "dependency additions must be human-approved"),
    (r"\b(pnpm|npm|yarn)\s+(add|install)\s+[^-]", "dependency additions must be human-approved"),
]


def block(reason: str) -> None:
    print(f"BLOCKED by .claude/hooks/protect_paths.py: {reason}", file=sys.stderr)
    # Also emit JSON that blocks in bypassPermissions mode.
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(2)


def relpath(abs_path: str) -> str:
    base = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    try:
        return os.path.relpath(abs_path, base)
    except ValueError:
        return abs_path


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # do not block on malformed input

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {}) or {}

    if tool in ("Edit", "Write", "MultiEdit"):
        path = inp.get("file_path") or inp.get("path") or ""
        rel = relpath(path)
        for pat in PROTECTED_PATHS:
            if re.search(pat, rel):
                block(f"{rel} is in a protected zone. Ask the human to edit it directly.")

    if tool == "Read":
        path = inp.get("file_path") or ""
        if re.search(r"(^|/)\.env(\.|$)", path) or path.endswith((".pem", ".key", "id_rsa")):
            block(
                "Secret files are not readable. "
                "Reference .env.example if you need environment variable names."
            )

    if tool == "Bash":
        cmd = inp.get("command", "")
        for pat, reason in DANGEROUS_BASH:
            if re.search(pat, cmd):
                block(f"Command matches deny pattern: {reason}")
        # Also block attempts to read protected files via cat/less/head/tail
        for pat in PROTECTED_PATHS:
            if re.search(rf"\b(cat|less|more|head|tail|bat)\b.*{pat}", cmd):
                block("Reading protected file via shell is blocked.")
        if re.search(r"\bcat\b.*\.env", cmd) or re.search(r"\becho\b.*\$\{?[A-Z_]*SECRET", cmd):
            block("Attempt to read or echo secrets is blocked.")

    sys.exit(0)


if __name__ == "__main__":
    main()
