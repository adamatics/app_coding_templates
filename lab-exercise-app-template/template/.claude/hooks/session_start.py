#!/usr/bin/env python3
"""session_start — SessionStart hook announcing the guardrails (Addendum A §A4).

Prints a short notice (added to the session context) so the agent knows, up front, that the
chassis is protected and the exercise seam is the place to work.
"""
import sys


def main() -> None:
    sys.stdout.write(
        "🛡️  Guardrails are active for this lab-exercise app.\n"
        "This is a chassis/seam template: the CHASSIS (backend, frontend, deploy config) is\n"
        "protected by a PreToolUse hook and never edited per app. To change the exercise,\n"
        "edit ONLY the seam:\n"
        "  exercise/schema.py   exercise/analysis.py   exercise/content.md\n"
        "The form, results table, charts and export columns all follow from schema.py.\n"
        "See .claude/CLAUDE.md and the lab-exercise-app skill. Run /new-exercise-field to add\n"
        "a measurement field.\n"
    )


if __name__ == "__main__":
    main()
