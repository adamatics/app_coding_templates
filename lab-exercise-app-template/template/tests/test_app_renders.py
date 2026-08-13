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


# --- coming back later: the session must survive leaving the app -------------
#
# Reported from the deployed app: "when I go to the app url again after having registered I
# get asked for the course password again, and then to re-register." The token was kept only
# in the URL (`?s=…`), which survives a refresh but not the thing students actually do — open
# the app from the gallery, a bookmark, or a link, all of which load the bare URL. Every visit
# then created a duplicate registration.
def test_the_session_token_is_not_only_in_the_url(app):
    """The token must be written somewhere the browser keeps, not just the address bar."""
    from ui import session_url

    source = (Path(session_url.__file__)).read_text(encoding="utf-8")
    assert "cookies" in source, (
        "session persistence must read a cookie as well as the URL parameter, or a student "
        "opening the app from the gallery is asked to register again every time")
    assert "st.context.cookies" in source, "read the cookie server-side, before anything renders"


def test_the_cookie_is_named_per_app():
    """Several CPDSE apps share one hostname — a shared cookie name crosses their sessions."""
    from core.config import settings
    from ui.session_url import _cookie_name

    name = _cookie_name()
    assert settings.project_slug.replace("-", "_") in name, \
        f"cookie name {name!r} must include the app slug"


def test_a_token_from_the_url_wins_over_the_cookie(monkeypatch):
    """An explicit link is a deliberate act; a cookie is not. Support depends on this."""
    from ui import session_url

    monkeypatch.setattr(session_url, "_from_url", lambda: "from-url")
    monkeypatch.setattr(session_url, "_from_cookie", lambda: "from-cookie")
    assert session_url.read_session_token() == "from-url"

    monkeypatch.setattr(session_url, "_from_url", lambda: None)
    assert session_url.read_session_token() == "from-cookie"


# --- the admin form: typing then clicking Save must save what was typed ------
#
# Reported from the deployed app: "saving an admin setting like the name does nothing." A bare
# st.text_input only sends its value on blur or Enter, so typing and clicking Save could store
# the PREVIOUS value — and the click that committed the text often did not register as a
# button press either. Inside a form, every field is submitted with the button in one go.
def test_the_course_settings_are_a_form(app):
    """The fix is structural, so the test is too: no bare Save button on this tab."""
    from ui import admin_page

    source = Path(admin_page.__file__).read_text(encoding="utf-8")
    assert 'st.form("course_settings")' in source, (
        "course settings must be a form; with bare widgets, typing a value and clicking Save "
        "can persist the value from before the edit")
    assert 'st.button("Save course settings"' not in source, \
        "the save control must be the form's submit button, not a separate st.button"


def test_saving_course_settings_persists_every_field(app):
    """End to end through the real app: sign in, open Admin, submit the form, read it back."""
    from core import admin as core_admin
    from core.db import get_session

    _pass_gate(app)
    _register(app)
    _button(app, "Admin").click().run()

    _input(app, "admin password").set_value("admin-secret")
    _button(app, "Sign in").click().run()
    _assert_clean(app, "admin signed in")

    _input(app, "Course name").set_value("Farmaceutisk kemi")
    _input(app, "Instructor").set_value("Dr Test")
    next(a for a in app.text_area if "banner" in a.label.lower()).set_value("Use fridge C")
    _button(app, "Save course settings").click().run()
    _assert_clean(app, "after saving course settings")

    with get_session() as session:
        assert core_admin.get_setting(session, "course_name") == "Farmaceutisk kemi"
        assert core_admin.get_setting(session, "instructor") == "Dr Test"
        assert core_admin.get_setting(session, "banner") == "Use fridge C"


def test_rendering_the_admin_tab_does_not_rewrite_the_settings(app):
    """The form body re-runs on every render; only a submit may write.

    Without this, any click anywhere in the app would rewrite every course setting with
    whatever the widgets last held — silently reverting an edit made in another tab.
    """
    from core import admin as core_admin
    from core.db import get_session

    with get_session() as session:
        core_admin.set_setting(session, "instructor", "Set Elsewhere")

    _pass_gate(app)
    _register(app)
    _button(app, "Admin").click().run()
    _input(app, "admin password").set_value("admin-secret")
    _button(app, "Sign in").click().run()
    # Re-render the tab a few times without submitting.
    _button(app, "My group").click().run()
    _button(app, "Admin").click().run()
    _assert_clean(app, "admin re-rendered")

    with get_session() as session:
        assert core_admin.get_setting(session, "instructor") == "Set Elsewhere", \
            "rendering the admin tab must not write settings — only the submit button may"


def test_a_rerun_from_another_widget_does_not_change_the_page(app):
    """Reported from the deployed app: "when hitting Enter I get taken out of the admin page".

    Pressing Enter in a text field reruns the script. Navigation used to be derived from the
    sidebar radio's return value, so any rerun re-asserted the radio's selection and threw the
    teacher back to the page they came from — mid-edit, losing what they had typed. Only a
    deliberate interaction with a navigation control may move the page.
    """
    _pass_gate(app)
    _register(app)
    _button(app, "Admin").click().run()
    _input(app, "admin password").set_value("admin-secret")
    _button(app, "Sign in").click().run()
    assert _state(app, "page") == "Admin"

    # The rerun a text field causes when the user presses Enter.
    _input(app, "Course name").set_value("Typed but not saved").run()
    _assert_clean(app, "after a rerun from a text field")
    assert _state(app, "page") == "Admin", (
        "a rerun caused by a text field must not navigate — the teacher was editing")

    # And again from a page that is not the one the radio remembers.
    _button(app, "My group").click().run()
    assert _state(app, "page") == "My group"
    _assert_clean(app, "my group")


def test_the_exercise_menu_shows_nothing_selected_on_a_secondary_page(app):
    """The sidebar must not claim the student is on "Data capture" while Admin is open."""
    _pass_gate(app)
    _register(app)
    assert _nav(app).value == "Data capture"

    _button(app, "Admin").click().run()
    assert _nav(app).value is None, (
        f"expected no exercise page highlighted while on Admin, got {_nav(app).value!r}")
