"""Course login gate (§B2, §B3). The course password is the access control."""
from __future__ import annotations

import streamlit as st

from core import events, identity, sessions
from core.config import settings
from core.db import get_session

from . import _components as C
from .session_url import remember_session_token


def render() -> None:
    # The sign-in page is the one place the full lock-up gets room to breathe.
    C.signin_logo()
    C.header(settings.exercise_title, settings.course_code)
    st.subheader("Course sign-in")
    st.caption("This app is open to your class via a course password (no personal account "
               "needed). Your instructor rotates it each semester.")

    if not settings.gate_enabled:
        C.notice("This course isn't configured yet — no course password is set. "
                 "Ask your instructor to set <code>COURSE_PASSWORD</code> and redeploy.", "err")
        return

    st.write(f"Course: **{settings.course_id}**")
    with st.form("course_gate"):
        password = st.text_input("Course password", type="password")
        entered = st.form_submit_button("Enter")
    if entered:
        if identity.check_course_password(password):
            st.session_state["gate_ok"] = True
            with get_session() as session:
                token = sessions.issue(session)          # gate-only until they register
                events.log(session, "course_gate_passed", detail={"course_id": settings.course_id})
            st.session_state["session_token"] = token
            remember_session_token(token)
            st.rerun()
        else:
            C.notice("That course password is not correct.", "err")
            with get_session() as session:
                events.log(session, "course_gate_failed", level=events.WARNING,
                           detail={"course_id": settings.course_id})

    C.footer(settings.institution_name, settings.contact_email)
