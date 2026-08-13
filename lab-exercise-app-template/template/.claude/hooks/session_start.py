#!/usr/bin/env python3
"""session_start — SessionStart hook announcing the guardrails (Addendum A §A4).

Prints a short notice (added to the session context) so the agent knows, up front, that the
chassis is protected and the exercise seam is the place to work.
"""
import sys


def main() -> None:
    sys.stdout.write(
        "🛡️  Guardrails are active for this lab-exercise app (Streamlit).\n"
        "Chassis/seam split: core/ (framework-free — imports streamlit NOWHERE), pages/ and\n"
        "app.py are CHASSIS and protected by a PreToolUse hook. To change the exercise, edit\n"
        "ONLY the seam:\n"
        "  exercise/schema.py  exercise/capture.py  exercise/analysis.py  exercise/content.md\n"
        "Storage, CSV/exports and the anonymised comparison follow from the schema; build\n"
        "plots with core.plots so each gets its 'Show the code' panel.\n"
        "See .claude/CLAUDE.md and the lab-exercise-app skill. Run /new-exercise-field to add\n"
        "a measurement field.\n"
    )


if __name__ == "__main__":
    main()
