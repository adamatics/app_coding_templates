"""Register / My group (§B2, §B3). KUID + name + hold, then join or create a group."""
from __future__ import annotations

import streamlit as st

from core import admin, events, identity, sessions
from core.db import get_session
from core.errors import CoreError
from core.models import Member

from . import _components as C
from .session_url import clear_session_token

HOLDS = list(range(1, 8))  # 7 holds per year (§B2)


def current_context():
    """The signed-in student's four identity levels, or None. Session-scoped by Streamlit."""
    member_id = st.session_state.get("member_id")
    if not member_id:
        return None
    with get_session() as session:
        member = session.get(Member, member_id)
        if member is None:
            return None
        return identity.member_context(session, member)


def render() -> None:
    """Onboarding step 2 when nobody is registered yet, "my group" afterwards.

    The same screen serves both, but the heading says which one the student is looking at:
    on the first visit this is a task to finish, later it is a record to check or change.
    """
    ctx = current_context()
    st.header("My group" if ctx else "Register")

    if ctx:
        C.notice(f"You're registered as <b>{ctx['display_name']}</b> (KUID {ctx['kuid']}) in "
                 f"group <b>{ctx['group']}</b>, hold {ctx['hold']}, {ctx['year']}.", "ok")
        st.caption("You'll stay signed in on this browser — a refresh won't lose your place.")
        if st.button("Sign out / switch student"):
            token = st.session_state.get("session_token")
            if token:
                with get_session() as session:
                    sessions.revoke(session, token)
            clear_session_token()
            st.session_state.clear()
            st.rerun()
        return

    with get_session() as session:
        try:
            cohort = identity.get_open_cohort(session)
        except CoreError as exc:
            C.notice(exc.message, "err")
            return
        group_layer = bool((admin.get_setting(session, "active_layers") or {}).get("group", True))

        st.caption("Enter your KUID (three letters + three digits, e.g. abc123) and your name.")
        kuid = st.text_input("KUID")
        name = st.text_input("Your name")

        group_id = None
        new_group_name = None
        hold = 1
        if group_layer:
            hold = st.selectbox("Hold", HOLDS, index=0)
            groups = identity.list_groups(session, cohort, hold)
            choice = st.radio("Group", ["Join an existing group", "Create a new group"],
                              horizontal=True)
            if choice == "Join an existing group":
                if groups:
                    labels = {f"{g.name}": g.id for g in groups}
                    pick = st.selectbox("Choose your group", list(labels))
                    group_id = labels[pick]
                else:
                    C.notice("No groups in this hold yet — create the first one.")
            else:
                new_group_name = st.text_input("New group name")
        else:
            new_group_name = None  # individual-only: a singleton group is auto-created below

    if st.button("Register"):
        with get_session() as session:
            try:
                if not group_layer and not new_group_name:
                    new_group_name = f"{kuid.strip() or 'me'}"  # singleton group per individual
                member = identity.register(session, kuid, name, hold,
                                           group_id=group_id, new_group_name=new_group_name)
                st.session_state["member_id"] = member.id
                # Bind the existing gate token to this student so the URL keeps working.
                token = st.session_state.get("session_token")
                if token:
                    sessions.attach_member(session, token, member.id)
            except CoreError as exc:
                C.notice(exc.message, "err")
                events.log(session, "registration_rejected", level=events.WARNING,
                           detail={"reason": exc.message})
                return
        st.rerun()
