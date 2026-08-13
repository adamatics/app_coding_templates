"""Navigation is defined in `app.py` and nowhere else.

**The incident this prevents.** The UI package used to be called `pages/`. Streamlit decides
whether to run in magic multipage mode from the *name of the directory* beside the entry
script — nothing else, no opt-in::

    # streamlit/runtime/pages_manager.py
    PagesManager.uses_pages_directory = Path(self.main_script_parent / "pages").exists()

Every `.py` in that directory then becomes a page with its own URL and its own sidebar entry.
Students opening the deployed app were shown a second menu listing `login`, `register`,
`session_url` and `components` — internal modules, not screens — each reachable by URL and
none of them going through `main()`, which is where the course gate lives.

Renaming the package to `ui/` is the entire fix, and it is a fix that a well-meaning later
change ("Streamlit convention is a pages/ folder") would silently undo. Hence this test.

The second half checks the menu a student is actually offered: three exercise pages, with
registration and admin one click away under "More". A page added to the wrong dict shows up
in a student's main menu, which is how this file catches design drift as well as regressions.
"""
from __future__ import annotations

from pathlib import Path

import app

APP_ROOT = Path(__file__).resolve().parent.parent


def test_no_directory_named_pages_beside_the_entry_script():
    """A directory called `pages/` next to app.py silently turns on Streamlit multipage mode."""
    magic = APP_ROOT / "pages"
    assert not magic.exists(), (
        "a directory named 'pages/' next to app.py makes Streamlit auto-register every module "
        "in it as a page — with its own URL, outside the course gate, and listed in a second "
        "sidebar menu. The UI package is called 'ui/' for exactly this reason; if you are "
        "adding a screen, add it to ui/ and register it in app.EXERCISE_PAGES.")


def test_the_ui_package_is_where_the_screens_live():
    assert (APP_ROOT / "ui" / "__init__.py").is_file(), \
        "the chassis UI package should be ui/ (see app.py's module docstring)"


def test_the_student_menu_is_the_exercise_only():
    """Three entries: what a student does. Everything else is under 'More'."""
    assert list(app.EXERCISE_PAGES) == ["Data capture", "Data analysis", "FAQ"]
    assert list(app.SECONDARY_PAGES) == ["My group", "Admin"]


def test_the_landing_page_is_an_exercise_page():
    """After registering, a student lands on the work — not on a settings screen."""
    assert app.LANDING_PAGE in app.EXERCISE_PAGES
    assert app.LANDING_PAGE == "Data capture"


def test_every_menu_entry_maps_to_something_callable():
    for label, render in app.PAGES.items():
        assert callable(render), f"{label!r} does not map to a render function"


def test_no_internal_module_is_exposed_as_a_page():
    """`login`, `session_url` and `_components` are machinery, not destinations.

    They are reachable only through `main()` (the gate) or by import — never as a menu entry
    a student can pick, and never as a URL.
    """
    internal = {"login", "session_url", "session url", "components", "_components", "admin_page"}
    offered = {label.lower() for label in app.PAGES}
    assert not (offered & internal), f"internal modules exposed as pages: {offered & internal}"
