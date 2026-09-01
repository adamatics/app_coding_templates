#!/usr/bin/env python3
"""session_start — SessionStart hook orienting the agent in the app.

Prints a short notice (added to the session context) so the agent knows where to start, what
is actually enforced, and what the one blocked zone is.
"""
import sys


def main() -> None:
    sys.stdout.write(
        "🧪 Lab-exercise app (Streamlit). Start at the seam:\n"
        "  exercise/schema.py  exercise/capture.py  exercise/analysis.py  exercise/content.md\n"
        "Storage, CSV/exports and the anonymised comparison all follow from the schema; build\n"
        "plots with core.plots so each keeps its 'Show the code' panel.\n"
        "core/, ui/, app.py and assets/ are EDITABLE. The invariants that matter are enforced\n"
        "by the test suite, not by a hook — core/ imports streamlit nowhere, and ui/ is never\n"
        "renamed pages/. After a chassis change run:\n"
        "  DATA_DIR=$(mktemp -d) python -m pytest -q\n"
        "Blocked: .adalab/{app,project,card}.json (deployment state) and commands that would\n"
        "delete the volume or the database.\n"
        "See .claude/CLAUDE.md and the lab-exercise-app skill. Run /new-exercise-field to add\n"
        "a measurement field.\n"
    )


if __name__ == "__main__":
    main()
