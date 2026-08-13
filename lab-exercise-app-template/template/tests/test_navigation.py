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


def test_navigation_is_driven_by_callbacks_not_widget_return_values():
    """The structural guard for "hitting Enter takes me out of the admin page".

    Navigation used to be derived from the sidebar radio's return value:

        chosen = st.radio(...)
        if chosen is not None and chosen != page:
            page = st.session_state["page"] = chosen

    In a browser the radio reports its stored selection on *every* rerun, including reruns
    nobody asked for — pressing Enter in a text field, a websocket reconnect. The comparison
    then "corrected" the page back to whatever the radio remembered, throwing a teacher out of
    the admin page mid-edit.

    A callback fires only on a genuine change, so a rerun from anywhere else cannot navigate.

    **This test is structural on purpose.** `AppTest` sets widget values directly and does not
    reproduce the browser's widget-state behaviour — the behavioural tests in
    `test_app_renders.py` pass against the broken version too. What can be pinned is the
    shape of the fix, so the pattern cannot come back unnoticed.
    """
    source = (APP_ROOT / "app.py").read_text(encoding="utf-8")

    assert "on_change=_nav_radio_changed" in source, \
        "the navigation radio must change the page through a callback"
    assert "key=NAV_KEY" in source, \
        "the navigation radio needs an explicit key so its state is addressable"
    assert "on_click=_select_page" in source, \
        "the secondary-page buttons must navigate through a callback, not an if-block"

    # The exact shape of the bug: comparing a widget's return value against the current page
    # and "correcting" the page to match. Assigning inside a callback is fine — that is the
    # fix — so the check targets the comparison, not the assignment.
    assert "chosen != page" not in source, (
        "the page must not be derived by comparing a widget's return value against it — that "
        "is the pattern that navigated on passive reruns")
    assert "= st.radio(" not in source, (
        "don't bind the navigation radio's return value; drive navigation from its on_change "
        "callback so only a real selection moves the page")


def test_only_the_navigation_helpers_assign_the_current_page():
    """One writer, so there is one place to look when navigation misbehaves."""
    source = (APP_ROOT / "app.py").read_text(encoding="utf-8")
    assignments = [line.strip() for line in source.splitlines()
                   if 'st.session_state["page"]' in line and "=" in line
                   and "==" not in line and not line.strip().startswith("#")]
    # `_select_page`, `_nav_radio_changed`, and the reset of a stale value on load.
    assert len(assignments) <= 3, (
        "more than three places assign the current page; navigation should stay in "
        f"_select_page/_nav_radio_changed:\n" + "\n".join(assignments))
