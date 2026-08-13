"""Entry point: gate, navigation, shared chrome (CHASSIS).

Note on ``pages/``: this app does its own navigation rather than using Streamlit's magic
multipage auto-discovery, because Addendum B fixes the package layout (``pages/`` holds the
chassis UI modules, not auto-registered page scripts). Every render goes through here, so the
course gate and the admin banner cannot be bypassed by deep-linking.
"""
from __future__ import annotations

import streamlit as st

from core import admin as core_admin, sessions, theme
from core.config import settings
from core.db import StorageError, get_session, init_db
from core.seed_demo import seed_demo_data
from pages import _components as C
from pages import admin_page, analysis, capture, faq, login, register
from pages.session_url import (
    clear_session_token,
    read_session_token,
    remember_session_token,
)

PAGES = {
    "Register / My group": register.render,
    "Data capture": capture.render,
    "Data analysis": analysis.render,
    "FAQ": faq.render,
    "Admin": admin_page.render,
}


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

    with st.sidebar:
        st.markdown(f"**{settings.exercise_title}**")
        st.caption(settings.course_code)
        choice = st.radio("Go to", list(PAGES), label_visibility="collapsed")
        st.markdown("---")
        ctx = register.current_context()
        if ctx:
            st.caption(f"{ctx['display_name']} · {ctx['group']} · hold {ctx['hold']} · {ctx['year']}")
        else:
            st.caption("Not registered yet")
        if st.button("Leave course"):
            token = st.session_state.get("session_token")
            if token:
                with get_session() as session:
                    sessions.revoke(session, token)
            clear_session_token()
            st.session_state.clear()
            st.rerun()

    # Error boundary: an unexpected failure in any page is logged with its traceback and
    # shown as a plain message, rather than a raw Streamlit stack trace (or, with
    # showErrorDetails off, a blank panel that tells nobody anything).
    try:
        PAGES[choice]()
    except Exception as exc:
        C.notice("<b>Sorry — something went wrong on this page.</b><br>"
                 "Your saved data is safe. Please try again, and tell your instructor if it "
                 "keeps happening.", "err")
        with get_session() as session:
            events.log_error(session, "page_failed", exc, context=ctx or {},
                             detail={"page": choice})

    C.footer(settings.institution_name, settings.contact_email)


if __name__ == "__main__":
    main()
