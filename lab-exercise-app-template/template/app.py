"""Entry point: gate, onboarding, navigation, shared chrome (CHASSIS).

**Why the UI package is called ``ui/`` and not ``pages/``.** Streamlit turns on magic
multipage mode purely from the *name* of the directory next to the entry script::

    PagesManager.uses_pages_directory = Path(main_script_parent / "pages").exists()

Every module in such a directory becomes its own page with its own URL, listed in the sidebar.
When this app's UI package was called ``pages/``, students were shown a second navigation menu
containing ``login``, ``register``, ``session_url`` and ``components`` — internal modules, not
screens — and each was reachable by URL outside this file's control. Renaming the package is
the whole fix; ``tests/test_navigation.py`` fails if a ``pages/`` directory ever comes back.

This app therefore does all its own navigation here. Every render goes through ``main()``, so
the course gate and the admin banner cannot be bypassed by deep-linking.

**The student's path through the app** is one-way and deliberately narrow:

1. *Course password* (``ui.login``) — the only gate; there are no student passwords (§B2).
2. *Register* (``ui.register``) — forced, full-screen, no navigation. A student who has not
   registered has no group, so nothing they submit could be attributed.
3. *The exercise* — capture, analysis, FAQ. This is where they live for the rest of the course,
   and where they land on every later visit, because the session token restores steps 1 and 2.

Registration and the admin console are one click away under "More" rather than sitting in the
main list: after the first visit, neither is part of doing the exercise.
"""
from __future__ import annotations

import streamlit as st

from core import admin as core_admin, events, sessions, theme
from core.config import settings
from core.db import StorageError, get_session, init_db
from core.seed_demo import seed_demo_data
from ui import _components as C
from ui import admin_page, analysis, capture, faq, login, register
from ui.session_url import (
    clear_session_token,
    read_session_token,
    remember_session_token,
)

# The exercise itself — the only three entries a student sees in the main menu.
EXERCISE_PAGES = {
    "Data capture": capture.render,
    "Data analysis": analysis.render,
    "FAQ": faq.render,
}

# Needed once (registration) or by teachers only (admin). Kept out of the main menu so the
# student's list is the work, not the plumbing — reachable under "More" in the sidebar.
SECONDARY_PAGES = {
    "My group": register.render,
    "Admin": admin_page.render,
}

PAGES = {**EXERCISE_PAGES, **SECONDARY_PAGES}
LANDING_PAGE = next(iter(EXERCISE_PAGES))


@st.cache_resource
def _bootstrap() -> dict:
    """Run once per process: fail-loud storage check, migrate, optional demo seed."""
    init_db()
    events.setup_logging()
    if settings.demo_mode:
        with get_session() as session:
            seed_demo_data(session)
    return {"ok": True}


def _restore_session() -> None:
    """Rehydrate the gate and identity from the URL token (§B2: no student passwords).

    Streamlit's session_state is lost on refresh or in a new tab; the opaque token in the URL
    is what lets a student reload — or come back weeks later — without re-entering the course
    password and their KUID.
    """
    if st.session_state.get("gate_ok") and st.session_state.get("member_id"):
        return
    token = read_session_token()
    if not token:
        return
    with get_session() as session:
        state = sessions.resolve(session, token)
    if state is None:
        clear_session_token()   # expired/unknown: show a clean gate rather than a dead URL
        return
    st.session_state["gate_ok"] = True
    st.session_state["session_token"] = token
    if state["member_id"] and not st.session_state.get("member_id"):
        st.session_state["member_id"] = state["member_id"]


def main() -> None:
    # Browser-tab icon: the CPDSE artwork when supplied, else a neutral emoji. Streamlit
    # rejects some formats for the favicon, so never let it stop the app from starting.
    page_icon: object = "🧪"
    icon_path = theme.asset_path("favicon") or theme.asset_path("cpdse-mark") \
        or theme.asset_path("cpdse-logo")
    if icon_path is not None and icon_path.suffix.lower() != ".svg":
        page_icon = str(icon_path)
    try:
        st.set_page_config(page_title=settings.exercise_title, page_icon=page_icon, layout="wide")
    except Exception:  # pragma: no cover - unsupported icon format
        st.set_page_config(page_title=settings.exercise_title, page_icon="🧪", layout="wide")
    C.inject_theme()

    try:
        _bootstrap()
    except StorageError as exc:
        # Fail loud, in the UI as well as the logs (§A3).
        C.header(settings.exercise_title, settings.course_code)
        C.notice("<b>Storage is not available, so the app cannot start safely.</b><br>"
                 f"<pre>{exc}</pre>", "err")
        events.log(None, "startup_storage_unavailable", level=events.ERROR,
                   detail={"error": str(exc)[:500]})
        st.stop()

    _restore_session()

    # Preview mode: no volume mounted and no course password, so the app is running on
    # scratch space (see core/config.py). Say so on every screen — including the gate —
    # so nobody mistakes a Test run for a working deployment.
    if settings.preview_mode:
        C.notice(
            "<b>Preview mode — not for students.</b> No storage volume is mounted, so "
            "anything entered here is lost when the app stops. Set "
            "<code>COURSE_PASSWORD</code> and mount the Shared Volume before using this "
            "with a class.", "err")
    elif settings.local_storage:
        # Deliberate (STORAGE_MODE=local), so this is a standing caution rather than a
        # fault — but it is on every screen, because "the results are gone" is discovered
        # far too late otherwise.
        C.notice(
            "<b>Results are stored on local disk, not a Shared Volume.</b> They are erased "
            "whenever this app is redeployed or restarted. Download an export from "
            "<b>More → Admin</b> after each session — it is the only copy.", "err")

    # Course gate (§B2) — everything below requires it.
    if not st.session_state.get("gate_ok"):
        login.render()
        return

    # Keep the URL token in sync so a refresh doesn't sign the student out.
    if st.session_state.get("session_token"):
        remember_session_token(st.session_state["session_token"])

    with get_session() as session:
        banner_text = core_admin.banner(session)

    C.header(settings.exercise_title, settings.course_code)
    C.banner(banner_text)

    ctx = register.current_context()

    # Step 2 of onboarding. Registration is a one-time step, so it is shown on its own with no
    # navigation to wander off into: an unregistered student has no group, and nothing they
    # entered could be attributed to anyone. `register.render()` reruns once it succeeds, and
    # the next pass lands on the exercise below.
    if ctx is None:
        with st.sidebar:
            _sidebar_identity(None)
            _leave_course_button()
        _render_page("My group", None)
        C.footer(settings.institution_name, settings.contact_email)
        return

    page = st.session_state.get("page") or LANDING_PAGE
    if page not in PAGES:                       # stale state from an older version
        page = LANDING_PAGE

    with st.sidebar:
        st.markdown(f"**{settings.exercise_title}**")
        st.caption(settings.course_code)

        # index=None leaves the radio unselected while a secondary page is open, so the
        # sidebar never claims the student is on "Data capture" when they are not.
        options = list(EXERCISE_PAGES)
        chosen = st.radio("Go to", options, label_visibility="collapsed",
                          index=options.index(page) if page in EXERCISE_PAGES else None)
        if chosen is not None and chosen != page:
            page = st.session_state["page"] = chosen

        with st.expander("More", expanded=page in SECONDARY_PAGES):
            for label in SECONDARY_PAGES:
                if st.button(label, use_container_width=True, key=f"nav_{label}"):
                    st.session_state["page"] = label
                    st.rerun()

        st.markdown("---")
        _sidebar_identity(ctx)
        _leave_course_button()

    _render_page(page, ctx)
    C.footer(settings.institution_name, settings.contact_email)


def _sidebar_identity(ctx) -> None:
    if ctx:
        st.caption(f"{ctx['display_name']} · {ctx['group']} · hold {ctx['hold']} · {ctx['year']}")
    else:
        st.caption("Step 2 of 2 — register to start")


def _leave_course_button() -> None:
    if st.button("Leave course"):
        token = st.session_state.get("session_token")
        if token:
            with get_session() as session:
                sessions.revoke(session, token)
        clear_session_token()
        st.session_state.clear()
        st.rerun()


def _render_page(page: str, ctx) -> None:
    """Render one page inside an error boundary.

    An unexpected failure is logged with its traceback and shown as a plain message, rather
    than a raw Streamlit stack trace (or, with showErrorDetails off, a blank panel that tells
    nobody anything).
    """
    try:
        PAGES[page]()
    except Exception as exc:
        C.notice("<b>Sorry — something went wrong on this page.</b><br>"
                 "Your saved data is safe. Please try again, and tell your instructor if it "
                 "keeps happening.", "err")
        with get_session() as session:
            events.log_error(session, "page_failed", exc, context=ctx or {},
                             detail={"page": page})


if __name__ == "__main__":
    main()
