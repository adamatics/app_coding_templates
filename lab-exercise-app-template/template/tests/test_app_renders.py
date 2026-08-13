"""The app actually runs, and every screen renders without blowing up.

This is the test that was missing when `app.py` shipped calling `events.setup_logging()`
without importing `events`. The unit tests all passed; the app crashed on its first page load.
Unit tests exercise `core/`, but nothing ran the Streamlit script itself.

Streamlit's own harness (`streamlit.testing.v1.AppTest`) executes the real script in-process,
so this covers the whole chain — page config, theme injection, bootstrap, the course gate,
registration, navigation, and each page's render — without a browser or a container.

**Why it also checks for the error notice, not just exceptions:** `main()` wraps page rendering
in an error boundary that logs the traceback and shows a friendly message. That is right for
students and wrong for tests — a broken page would otherwise look like a clean run. So a
rendered "something went wrong" notice fails these tests too.

The tests follow the student's actual path: password, register, then the exercise. Nothing is
reachable out of order, which is the property the sidebar redesign is supposed to guarantee.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1", reason="needs Streamlit's AppTest harness")

from streamlit.testing.v1 import AppTest  # noqa: E402

from tests.conftest import COURSE_PASSWORD, reset_db  # noqa: E402

# AppTest resolves a relative path against the file that calls it (tests/), not the cwd.
APP_FILE = str(Path(__file__).resolve().parent.parent / "app.py")

# The literal the error boundary in app.py renders. Kept here so a broken page cannot pass.
ERROR_BOUNDARY_TEXT = "something went wrong"


@pytest.fixture()
def app():
    """A fresh app on an empty database.

    The environment is set by `tests/conftest.py` before `core.config` is imported — settings
    are read once at import, so setting env vars in a fixture would be too late.
    """
    reset_db()
    return AppTest.from_file(APP_FILE, default_timeout=60)


# --- helpers ----------------------------------------------------------------
def _assert_clean(at: AppTest, where: str) -> None:
    assert not at.exception, (
        f"{where}: the app raised {[str(e.value)[:300] for e in at.exception]}")
    boundary_hits = [m.value for m in at.markdown if ERROR_BOUNDARY_TEXT in m.value.lower()]
    assert not boundary_hits, (
        f"{where}: the page hit the error boundary — the traceback is in the event log, and "
        f"the rendered message was: {boundary_hits[0][:200]}")


def _state(at: AppTest, key: str, default=None):
    """AppTest's session_state proxy raises rather than offering `.get()`."""
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


def _input(at: AppTest, label_fragment: str):
    for widget in at.text_input:
        if label_fragment.lower() in widget.label.lower():
            return widget
    raise AssertionError(
        f"no text input matching {label_fragment!r}; saw {[w.label for w in at.text_input]}")


def _button(at: AppTest, label: str):
    for widget in at.button:
        if widget.label == label:
            return widget
    raise AssertionError(f"no button {label!r}; saw {[w.label for w in at.button]}")


def _nav(at: AppTest):
    for radio in at.radio:
        if radio.label == "Go to":
            return radio
    raise AssertionError(f"no navigation radio; labels were {[r.label for r in at.radio]}")


def _has_nav(at: AppTest) -> bool:
    return any(radio.label == "Go to" for radio in at.radio)


def _headers(at: AppTest) -> list[str]:
    return [h.value for h in at.header]


def _pass_gate(at: AppTest) -> AppTest:
    at.run()
    _assert_clean(at, "course gate")
    _input(at, "password").set_value(COURSE_PASSWORD)
    at.button[0].click().run()
    _assert_clean(at, "after entering the course password")
    return at


def _register(at: AppTest, kuid: str = "abc123", name: str = "Test Student") -> AppTest:
    """Complete onboarding step 2. No groups exist yet, so create one."""
    group_choice = next(r for r in at.radio if r.label == "Group")
    group_choice.set_value("Create a new group").run()
    _assert_clean(at, "registration form")

    _input(at, "KUID").set_value(kuid)
    _input(at, "your name").set_value(name)
    _input(at, "new group name").set_value("Group A")
    _button(at, "Register").click().run()
    _assert_clean(at, "after registering")
    return at


# --- the gate ---------------------------------------------------------------
def test_the_gate_renders_before_anything_else(app):
    """The unauthenticated landing screen must render — this is what a student sees first."""
    app.run()
    _assert_clean(app, "initial load")
    assert any("password" in t.label.lower() for t in app.text_input), \
        "the course gate should ask for a password"
    assert not _state(app, "gate_ok"), "the gate must not open by itself"
    assert not _has_nav(app), "no navigation before the course password"


def test_a_wrong_password_keeps_the_gate_closed(app):
    app.run()
    _input(app, "password").set_value("not-the-password")
    app.button[0].click().run()
    _assert_clean(app, "after a wrong password")
    assert not _state(app, "gate_ok")
    assert not _has_nav(app)


# --- onboarding -------------------------------------------------------------
def test_the_password_leads_straight_to_registration(app):
    """Step 1 hands over to step 2 with no menu in between — the student has one thing to do."""
    _pass_gate(app)
    assert _state(app, "gate_ok") is True
    assert "Register" in _headers(app), f"expected the registration screen, saw {_headers(app)}"
    assert not _has_nav(app), (
        "an unregistered student must not see the exercise menu — there is nothing they can "
        "usefully do there, and anything they entered could not be attributed to a group")


def test_registering_lands_on_the_exercise(app):
    """The end of onboarding: the menu appears and the student is on the first exercise page."""
    _pass_gate(app)
    _register(app)

    assert _has_nav(app), "the exercise menu should appear once a student is registered"
    assert _state(app, "member_id"), "registration should have created a member"
    assert _nav(app).value == "Data capture", (
        f"a registered student should land on the exercise, not on {_nav(app).value!r}")


# --- navigation -------------------------------------------------------------
def test_the_menu_shows_only_the_exercise(app):
    """The regression this redesign is for: internal modules must never appear as menu items.

    When the UI package was called `pages/`, Streamlit added `login`, `register`,
    `session_url` and `components` to its own sidebar menu. Those names must not be offered
    to a student under any spelling.
    """
    _pass_gate(app)
    _register(app)

    assert _nav(app).options == ["Data capture", "Data analysis", "FAQ"]
    forbidden = {"login", "session_url", "session url", "components", "_components", "admin_page"}
    offered = {option.lower() for option in _nav(app).options}
    assert not (offered & forbidden), f"internal modules offered as pages: {offered & forbidden}"


@pytest.mark.parametrize("page", ["Data capture", "Data analysis", "FAQ"])
def test_every_exercise_page_renders_with_no_data_yet(app, page):
    """Each page must survive being opened by the first student of a new cohort.

    An empty database is the state most likely to break an analysis page written against a
    populated DataFrame, and it is the state every cohort starts in.
    """
    _pass_gate(app)
    _register(app)
    _nav(app).set_value(page).run()
    _assert_clean(app, f"page {page!r}")


@pytest.mark.parametrize("page", ["My group", "Admin"])
def test_the_secondary_pages_render_from_the_more_menu(app, page):
    _pass_gate(app)
    _register(app)
    _button(app, page).click().run()
    _assert_clean(app, f"secondary page {page!r}")
    assert _state(app, "page") == page


def test_the_admin_page_stays_locked_without_the_admin_password(app):
    _pass_gate(app)
    _register(app)
    _button(app, "Admin").click().run()
    _assert_clean(app, "admin page (locked)")
    assert any("password" in t.label.lower() for t in app.text_input), \
        "the admin page must ask for its own password"


def test_leaving_the_course_returns_to_the_gate(app):
    """Signing out must drop all the way back to step 1, not to a half-open state."""
    _pass_gate(app)
    _register(app)
    _button(app, "Leave course").click().run()
    _assert_clean(app, "after leaving the course")
    assert not _state(app, "gate_ok")
    assert not _state(app, "member_id")
    assert not _has_nav(app)
