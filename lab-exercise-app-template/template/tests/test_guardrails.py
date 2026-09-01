"""Guardrail integrity — the three layers must keep naming the same (short) set of files.

The guard is deliberately narrow: application code is editable, and only AdaLab deployment
state and student data are blocked (see DECISIONS.md, "Guardrail relaxation"). Two failure
modes are worth a test:

* **Drift.** The hook's ``PROTECTED`` list, ``permissions.deny`` in ``.claude/settings.json``
  and the list in ``.claude/CLAUDE.md`` are three copies of one set. They drifted before — the
  template SPEC listed ``pages/**`` as protected long after the directory was renamed to
  ``ui/`` — and nothing caught it.
* **Quiet re-tightening.** The relaxation only holds while `core/`, `ui/`, `app.py` and the
  seam stay unblocked, so that is asserted directly rather than left to review.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "deploy_guard.py"
SETTINGS = ROOT / ".claude" / "settings.json"
CLAUDE_MD = ROOT / ".claude" / "CLAUDE.md"

EXPECTED_PROTECTED = {
    ".adalab/app.json",
    ".adalab/project.json",
    ".adalab/card.json",
}

# Editable by design. A regression here means the guardrail has been quietly re-tightened.
MUST_STAY_EDITABLE = [
    "core/db.py",
    "core/theme.py",
    "ui/admin_page.py",
    "app.py",
    "assets/cpdse-logo.png",
    "exercise/schema.py",
    "Containerfile",
    "pyproject.toml",
    ".streamlit/config.toml",
    ".adalab/local_container_1.json",   # permissions.ask tier, not hook-blocked
    ".claude/settings.json",
    ".claude/hooks/deploy_guard.py",
]


def _load_hook():
    spec = importlib.util.spec_from_file_location("deploy_guard", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_hook(event: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
        env={"CLAUDE_PROJECT_DIR": str(ROOT), "PATH": "/usr/bin:/bin"},
    )


def _deny_paths() -> set[str]:
    perms = json.loads(SETTINGS.read_text())["permissions"]["deny"]
    return {rule.split("(", 1)[1].rstrip(")") for rule in perms}


# --- layer agreement --------------------------------------------------------
def test_hook_protects_exactly_the_deploy_state():
    assert set(_load_hook().PROTECTED) == EXPECTED_PROTECTED


def test_settings_deny_matches_the_hook():
    assert _deny_paths() == EXPECTED_PROTECTED, (
        "permissions.deny and the hook's PROTECTED list must name the same files")


def test_settings_deny_covers_every_edit_tool():
    perms = json.loads(SETTINGS.read_text())["permissions"]["deny"]
    for path in EXPECTED_PROTECTED:
        for tool in ("Edit", "Write", "MultiEdit"):
            assert f"{tool}({path})" in perms, f"missing deny rule: {tool}({path})"


def test_claude_md_names_the_same_blocked_files():
    text = CLAUDE_MD.read_text() if CLAUDE_MD.exists() else ""
    if not text:
        pytest.skip("CLAUDE.md is rendered from a .jinja template; not present in the source tree")
    blocked = text.split("## Blocked", 1)[1].split("##", 1)[0]
    for path in EXPECTED_PROTECTED:
        assert path in blocked, f"CLAUDE.md's blocked list omits {path}"


def test_local_container_config_is_ask_not_deny():
    ask = json.loads(SETTINGS.read_text())["permissions"]["ask"]
    assert "Edit(.adalab/local_container_1.json)" in ask
    assert ".adalab/local_container_1.json" not in _deny_paths()


# --- the hook actually behaves that way -------------------------------------
@pytest.mark.parametrize("rel", sorted(EXPECTED_PROTECTED))
def test_hook_blocks_deploy_state(rel):
    result = _run_hook({"tool_name": "Edit", "tool_input": {"file_path": rel}})
    assert result.returncode == 2, f"{rel} should be blocked"
    assert "deployment state" in result.stderr


@pytest.mark.parametrize("rel", MUST_STAY_EDITABLE)
def test_hook_allows_application_code(rel):
    result = _run_hook({"tool_name": "Edit", "tool_input": {"file_path": rel}})
    assert result.returncode == 0, f"{rel} must stay editable, got:\n{result.stderr}"


@pytest.mark.parametrize("command", [
    "rm -rf /asv-mnt/lab-data",
    "rm data/results.sqlite",
    "rm -rf .adalab",
])
def test_hook_blocks_destructive_commands(command):
    result = _run_hook({"tool_name": "Bash", "tool_input": {"command": command}})
    assert result.returncode == 2, f"should refuse: {command}"


@pytest.mark.parametrize("command", [
    "python -m pytest -q",
    "rm -rf .devapp",
    "git rm --cached core/db.py",
    "podman build -t lab .",
])
def test_hook_allows_ordinary_commands(command):
    result = _run_hook({"tool_name": "Bash", "tool_input": {"command": command}})
    assert result.returncode == 0, f"should allow: {command}\n{result.stderr}"


def test_escape_hatch_lifts_the_guard():
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": ".adalab/app.json"}}),
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
        env={"CLAUDE_PROJECT_DIR": str(ROOT), "PATH": "/usr/bin:/bin",
             "ALLOW_DEPLOY_CONFIG_EDIT": "1"},
    )
    assert result.returncode == 0
