"""Data capture (§B3): hosts the exercise-specific input UI from ``exercise/capture.py``.

Values are validated against ``exercise/schema.py`` on submit by the chassis. Results are
append-only: a mistake is fixed with a correction that supersedes, never an edit.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import documents as core_documents, events, exercise_bridge, results as results_core
from core.db import get_session
from core.errors import CoreError
from exercise import capture as seam_capture

from . import _components as C
from . import faq as faq_page
from .register import current_context


def render() -> None:
    st.header("Data capture")
    ctx = current_context()
    if not ctx:
        C.notice("Please register first (see <b>Register / My group</b>) — choosing your group "
                 "is how the app knows the result is yours.", "err")
        return

    st.caption(f"Recording as {ctx['display_name']} · group {ctx['group']} · hold {ctx['hold']} "
               f"· {ctx['year']}")

    # The lab manual, at the bench, without leaving the page.
    with get_session() as session:
        docs = core_documents.list_documents(session)
    if docs:
        with st.expander("📄 Course documents"):
            faq_page.render_documents(docs, heading="", key_prefix="capture")

    # The exercise's own "what to enter here" text, if the author provided one.
    intro = getattr(seam_capture, "render_intro", None)
    if callable(intro):
        try:
            intro()
        except Exception as exc:
            events.log_error(None, "seam_intro_failed", exc)

    correcting = st.session_state.get("correcting_result_id")
    defaults = st.session_state.get("correcting_defaults") if correcting else None
    if correcting:
        C.notice("You're submitting a <b>correction</b>. Your earlier reading is kept for the "
                 "record and replaced by this one.")

    payload = seam_capture.render_form(defaults)
    if payload is not None:
        try:
            clean = exercise_bridge.validate_payload(payload)
        except CoreError as exc:
            C.notice(f"Please check your entry — {exc.message}", "err")
            # Not an app error, but worth recording: repeated rejections usually mean the
            # form or the instructions are unclear, which the teacher wants to know.
            with get_session() as session:
                events.log(session, "submission_rejected", level=events.WARNING, context=ctx,
                           detail={"reason": exc.message, "correcting": bool(correcting)})
            return
        with get_session() as session:
            try:
                if correcting:
                    results_core.supersede_result(session, correcting, clean)
                    st.session_state.pop("correcting_result_id", None)
                    st.session_state.pop("correcting_defaults", None)
                else:
                    results_core.submit_result(session, ctx["member_id"], clean)
            except CoreError as exc:
                C.notice(exc.message, "err")
                events.log(session, "submission_refused", level=events.WARNING, context=ctx,
                           detail={"reason": exc.message})
                return
            except Exception as exc:
                C.notice("Something went wrong saving your result. Please try again — and "
                         "tell your instructor if it keeps happening.", "err")
                events.log_error(session, "submission_failed", exc, context=ctx)
                return
        C.notice("Saved. Your values are stored — scroll down to see them.", "ok")
        st.rerun()

    if correcting and st.button("Cancel correction"):
        st.session_state.pop("correcting_result_id", None)
        st.session_state.pop("correcting_defaults", None)
        st.rerun()

    _render_own_results(ctx)


def _render_own_results(ctx: dict) -> None:
    st.subheader("Your group's results so far")
    with get_session() as session:
        rows = results_core.results_for_scope(session, ctx, "group", latest=True)
    if not rows:
        st.caption("Nothing submitted yet.")
        return
    frame = pd.DataFrame(results_core.flat_rows(rows), columns=results_core.columns())
    st.dataframe(frame, use_container_width=True, hide_index=True)

    own = [r for r in rows if r["member_id"] == ctx["member_id"]]
    if own:
        labels = {f"#{r['id']} · {r['values'].get(exercise_bridge.field_names()[0], '')}"
                  f" · {r['submitted_at'][:10]}": r for r in own}
        pick = st.selectbox("Correct one of your results", ["—"] + list(labels))
        if pick != "—" and st.button("Start correction"):
            chosen = labels[pick]
            st.session_state["correcting_result_id"] = chosen["id"]
            st.session_state["correcting_defaults"] = chosen["values"]
            st.rerun()
