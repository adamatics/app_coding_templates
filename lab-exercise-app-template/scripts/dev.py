#!/usr/bin/env python3
"""Live preview of the template's UI — edit `template/`, see it in the browser immediately.

**Why this exists.** `copier → build → test` is a release gate, not an edit loop. Running it
after every layout tweak costs minutes and tells you nothing about how the page *looks*: the
container proves it starts, and AppTest proves the widgets are there, but neither can show you
spacing, colour, or whether a chart crowds its caption.

**What makes this possible.** Copier only renders files ending in `.jinja` (`_templates_suffix`
in copier.yml). Exactly one Python file in the whole template is templated —
`core/config.py.jinja` — and nothing under `ui/` is. So every file you touch while designing
can be *symlinked* out of the template rather than copied. Streamlit resolves the symlink,
watches the real file, and reruns on save. You edit the template; the browser updates.

    python3 scripts/dev.py

Then leave it running and edit `template/{{project_slug}}/ui/**` or `exercise/**`. Saving a
file reruns the app. Only a change to a `.jinja` file needs `--rebuild`.

Demo data is seeded by default, because an empty app hides most layout problems: charts have
no axes, tables have no rows, and every list is a placeholder. Use `--empty` to check the
first-run state deliberately.

This is a template-maintainer tool. It is not part of a stamped app and never ships to a
student — a stamped app is run with `streamlit run app.py`, or in its container.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Two layouts exist and both must work: the development repo nests the app under
# template/{{project_slug}}/ (so a stamp lands in its own folder), while the published
# monorepo flattens it to template/ (so `copier copy <dir> my-app` fills my-app directly).
_NESTED = REPO / "template" / "{{project_slug}}"
TEMPLATE = _NESTED if _NESTED.is_dir() else REPO / "template"

DEV_APP = REPO / ".devapp"

# Fixed answers so the stamped shell is stable across restarts and never prompts.
ANSWERS = {
    "project_name": "Dev Preview",
    "project_slug": "dev-preview",
    "exercise_title": "Spectrophotometric Absorbance Measurement",
    "course_code": "PHARMA-101",
    "contact_email": "dev@example.org",
}

# Directories whose plain files are linked back to the template. Everything a designer edits.
LINKED_TREES = ("ui", "core", "exercise", "assets", "tests", ".streamlit")


def _fail(message: str) -> None:
    sys.exit(f"dev.py: {message}")


def stamp() -> None:
    """Render the template once into .devapp/ (the .jinja files are the only real work)."""
    if DEV_APP.exists():
        shutil.rmtree(DEV_APP)
    if not shutil.which("copier"):
        _fail("copier is not installed — `pip install copier`")

    command = ["copier", "copy", str(REPO), str(DEV_APP.parent / "_devstamp"),
               "--defaults", "--trust"]
    for key, value in ANSWERS.items():
        command += ["-d", f"{key}={value}"]

    staging = DEV_APP.parent / "_devstamp"
    if staging.exists():
        shutil.rmtree(staging)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        _fail(f"copier failed:\n{result.stdout}\n{result.stderr}")

    stamped = staging / ANSWERS["project_slug"]
    if not stamped.is_dir():                       # flattened layout (the published repo)
        stamped = staging
    shutil.move(str(stamped), str(DEV_APP))
    shutil.rmtree(staging, ignore_errors=True)


def render_is_stale() -> str | None:
    """Name a `.jinja` file that changed since the last render, if any.

    Without this check, editing a `.jinja` file leaves `.devapp/` holding the *previous*
    render while every plain file is live — so the app runs a mix of old and new code and
    fails somewhere unrelated. Editing `core/config.py.jinja` to add a setting, for instance,
    surfaces as `AttributeError: 'Settings' object has no attribute ...` inside a page. The
    cost of checking is a few stat() calls; the cost of not checking is a confusing bug hunt.
    """
    marker = DEV_APP / "core" / "config.py"        # the one rendered file the app imports
    if not marker.exists():
        return "core/config.py"
    rendered_at = marker.stat().st_mtime
    for source in TEMPLATE.rglob("*.jinja"):
        if source.stat().st_mtime > rendered_at:
            return str(source.relative_to(TEMPLATE))
    return None


def link_back() -> tuple[int, int]:
    """Replace every non-templated file in .devapp/ with a symlink to the template source.

    A file that Copier rendered (`config.py` from `config.py.jinja`) is left as a real file —
    it holds substituted values and has no single source to point at.
    """
    linked = kept = 0
    for tree in LINKED_TREES:
        source_tree, dev_tree = TEMPLATE / tree, DEV_APP / tree
        if not source_tree.is_dir():
            continue
        for source in source_tree.rglob("*"):
            if not source.is_file() or "__pycache__" in source.parts:
                continue
            if source.name.endswith(".jinja"):     # rendered — keep the generated copy
                kept += 1
                continue
            target = dev_tree / source.relative_to(source_tree)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                target.unlink()
            target.symlink_to(source)
            linked += 1

    app_py = DEV_APP / "app.py"                    # the entry point is plain too
    if app_py.exists() or app_py.is_symlink():
        app_py.unlink()
    app_py.symlink_to(TEMPLATE / "app.py")
    return linked + 1, kept


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--empty", action="store_true",
                        help="start with no demo data, to inspect the first-run state")
    parser.add_argument("--rebuild", action="store_true",
                        help="re-render the .jinja files (needed only when you edit one)")
    parser.add_argument("--data-dir", default=str(REPO / ".devdata"),
                        help="where the dev database lives; delete it to start a fresh cohort")
    args = parser.parse_args()

    if not TEMPLATE.is_dir():
        _fail(f"template not found at {TEMPLATE}")

    stale = render_is_stale()
    if args.rebuild or not (DEV_APP / "app.py").exists():
        print("• rendering the template (only .jinja files need this) …")
        stamp()
    elif stale:
        print(f"• {stale} changed since the last render — re-rendering …")
        stamp()

    linked, rendered = link_back()
    print(f"• {linked} files linked live from template/, {rendered} rendered from .jinja")

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    environment = {
        **os.environ,
        "DATA_DIR": str(data_dir),
        "COURSE_PASSWORD": "dev",
        "ADMIN_PASSWORD": "dev",
        "DEMO_MODE": "false" if args.empty else "true",
        "PYTHONPATH": str(DEV_APP),
    }

    print(f"• course password 'dev', admin password 'dev'"
          f"{' — no demo data' if args.empty else ' — demo data seeded'}")
    print(f"• http://localhost:{args.port}  (edit template/ and save; the page reruns)\n")

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         f"--server.port={args.port}",
         "--server.headless=true",
         "--server.runOnSave=true",           # the whole point: save a file, see the change
         "--browser.gatherUsageStats=false"],
        cwd=DEV_APP, env=environment,
    )


if __name__ == "__main__":
    main()
