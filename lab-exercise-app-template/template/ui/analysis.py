"""Data analysis (§B3, §B4, §B5, §B7).

Renders the teacher's questions from ``exercise/content.md`` with free-text answer fields,
the retrieval-scope control, the exercise's visualisations (each with a "Show the code"
panel), and the export block.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import admin, analysis as core_analysis, events, exercise_bridge, export as core_export
from core import results as results_core
from core.config import settings
from core.db import get_session
from core.models import Answer, Member
from exercise import analysis as seam_analysis

from . import _components as C
from .register import current_context

SCOPE_LABELS = {
    "own": "Just me",
    "group": "My group",
    "neighbour": "My group + neighbouring group",
    "hold": "My hold",
    "year": "This year (whole class)",
    "all": "All years",
}
EXPORT_CSV_NAME = "results.csv"


def render() -> None:
    st.header("Data analysis")
    ctx = current_context()
    if not ctx:
        C.notice("Please register first (see <b>Register / My group</b>).", "err")
        return

    instructions, questions = exercise_bridge.content_sections()

    with get_session() as session:
        cap = admin.max_scope(session)
        scopes = results_core.allowed_scopes(cap)
        default_scope = "group" if "group" in scopes else scopes[0]
        scope = st.selectbox("Compare with", scopes,
                             index=scopes.index(default_scope),
                             format_func=lambda s: SCOPE_LABELS.get(s, s))
        st.caption("Classmates work at different paces, so results appear as they arrive — "
                   "you can come back later while writing your report.")

        own_rows = results_core.results_for_scope(session, ctx, "group", latest=True)
        compare_rows = results_core.results_for_scope(session, ctx, scope, latest=True)
        stats = core_analysis.summarize(compare_rows)

    anonymise = scope not in ("own", "group")
    own_df = core_analysis.to_dataframe(own_rows, anonymise=False)
    compare_df = core_analysis.to_dataframe(compare_rows, anonymise=anonymise)

    st.subheader("Your data")
    if own_df.empty:
        st.caption("No results captured yet.")
    else:
        st.dataframe(own_df, use_container_width=True, hide_index=True)

    st.subheader(f"Comparison — {SCOPE_LABELS.get(scope, scope)}")
    if anonymise:
        st.caption("Shown without names or group labels: distributions and summary statistics only.")
    if stats["n"]:
        summary = pd.DataFrame(stats["fields"]).T
        st.dataframe(summary, use_container_width=True)
    else:
        st.caption("No comparison data yet.")

    # --- plots with "Show the code" (§B7) ---
    plots = _safe_build_plots(own_df, compare_df)
    if plots:
        st.subheader("Plots")
        for p in plots:
            st.markdown(f"**{p['title']}**")
            C.show_the_code(p["figure"], p["code"])

    _render_questions(ctx, instructions, questions)
    _render_export(ctx, own_rows, compare_rows, plots, questions)


def _safe_build_plots(own_df: pd.DataFrame, compare_df: pd.DataFrame) -> list[dict]:
    """A seam bug must not take the page down — but it must be logged, not swallowed."""
    try:
        return seam_analysis.build_plots(own_df, compare_df, source=EXPORT_CSV_NAME)
    except Exception as exc:
        C.notice(f"The exercise's plots could not be built: {exc}", "err")
        with get_session() as session:
            events.log_error(session, "seam_plots_failed", exc)
        return []


def _render_questions(ctx: dict, instructions: str, questions: list[dict]) -> None:
    if not questions:
        return
    st.subheader("Questions")
    with st.expander("Exercise instructions"):
        st.markdown(instructions)
    with get_session() as session:
        existing = {a.question_id: a.text for a in
                    session.query(Answer).filter(Answer.group_id == ctx["group_id"]).all()}
    with st.form("answers"):
        drafts: dict[str, str] = {}
        for q in questions:
            drafts[q["id"]] = st.text_area(q["prompt"], value=existing.get(q["id"], ""),
                                           key=f"ans_{q['id']}")
        saved = st.form_submit_button("Save answers")
    if saved:
        with get_session() as session:
            for qid, text in drafts.items():
                row = session.query(Answer).filter(
                    Answer.group_id == ctx["group_id"], Answer.question_id == qid).one_or_none()
                if row is None:
                    session.add(Answer(group_id=ctx["group_id"], question_id=qid, text=text))
                else:
                    row.text = text
            session.commit()
            events.log(session, "answers_saved", context=ctx,
                       detail={"question_ids": sorted(drafts), "chars":
                               {q: len(t or "") for q, t in drafts.items()}})
        C.notice("Answers saved for your group.", "ok")


def _render_export(ctx: dict, own_rows: list[dict], compare_rows: list[dict],
                   plots: list[dict], questions: list[dict]) -> None:
    st.subheader("Export")
    st.caption("Take your data with you — apps get retired and passwords get forgotten. "
               "The CSV is what the 'Show the code' snippets read.")

    scope_choice = st.radio("What to export", ["My group's data", "The comparison I'm viewing"],
                            horizontal=True)
    rows = own_rows if scope_choice.startswith("My group") else compare_rows
    anonymise = not scope_choice.startswith("My group")

    with get_session() as session:
        answers = [{"prompt": q["prompt"],
                    "text": next((a.text for a in session.query(Answer).filter(
                        Answer.group_id == ctx["group_id"], Answer.question_id == q["id"]).all()), "")}
                   for q in questions]
        members = [m.display_name for m in
                   session.query(Member).filter(Member.group_id == ctx["group_id"]).all()]
        course = admin.get_setting(session, "course_name") or settings.exercise_title
        instructor = admin.get_setting(session, "instructor") or ""

    report_ctx = core_export.ReportContext(
        title=settings.exercise_title, course=course, instructor=instructor,
        year=ctx["year"], hold=ctx["hold"], group=ctx["group"], members=members,
        rows=rows, answers=answers,
        plots=[core_export.ReportPlot(title=p["title"], figure=p["figure"], code=p["code"])
               for p in plots],
    )
    base = f"{settings.project_slug}_{ctx['year']}_{ctx['group'].replace(' ', '-')}"

    def _log(fmt: str):
        """Runs only when the button is actually clicked (download_button renders every rerun)."""
        def handler():
            with get_session() as session:
                core_export.log_export(session, fmt, context=ctx, scope=scope_choice,
                                       rows=len(rows), anonymised=anonymise)
        return handler

    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("CSV", core_export.to_csv(rows, anonymise=anonymise),
                       file_name=EXPORT_CSV_NAME, mime="text/csv", on_click=_log("csv"))
    c2.download_button("Excel", core_export.to_excel(rows, anonymise=anonymise),
                       file_name=f"{base}.xlsx", on_click=_log("excel"),
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    try:
        c3.download_button("PDF report", core_export.build_pdf_report(report_ctx),
                           file_name=f"{base}.pdf", mime="application/pdf", on_click=_log("pdf"))
    except Exception as exc:
        c3.caption("PDF report unavailable — use the HTML report.")
        with get_session() as session:
            events.log_error(session, "export_pdf_failed", exc, context=ctx)
    c4.download_button("HTML report", core_export.build_html_report(report_ctx).encode("utf-8"),
                       file_name=f"{base}.html", mime="text/html", on_click=_log("html"))
