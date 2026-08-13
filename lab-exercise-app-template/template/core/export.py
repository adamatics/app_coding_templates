"""Exports (§B5): CSV, Excel, PDF report, HTML report. CHASSIS, framework-free (no streamlit).

CSV/Excel share the stable column order (schema fields + meta), so exports from different
cohorts of the same exercise concatenate directly (§B10). The PDF/HTML report combines the
group's captured data, their free-text answers, and the analysis plots into one document —
the thing students keep after the app is retired (§B5).
"""
from __future__ import annotations

import html
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
from plotly.graph_objs import Figure

from . import events, theme
from .results import columns, flat_rows, rows_to_csv


def log_export(session, fmt: str, *, context: Optional[dict[str, Any]] = None,
               scope: str = "", rows: int = 0, anonymised: bool = False,
               actor: Optional[str] = None) -> None:
    """Record that an export was actually taken.

    Call this from the download button's ``on_click``, never from the builders above:
    Streamlit renders ``st.download_button`` (and therefore builds the bytes) on every rerun,
    so logging inside a builder would record exports nobody downloaded.
    """
    events.log(session, "export_generated", actor=actor, context=context,
               detail={"format": fmt, "scope": scope, "rows": rows, "anonymised": anonymised})


@dataclass
class ReportPlot:
    title: str
    figure: Figure
    code: str = ""


@dataclass
class ReportContext:
    title: str
    course: str = ""
    instructor: str = ""
    year: str = ""
    hold: int = 0
    group: str = ""
    members: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)  # result rows (query_results shape)
    answers: list[dict[str, str]] = field(default_factory=list)  # [{"prompt":, "text":}]
    plots: list[ReportPlot] = field(default_factory=list)


# --- tabular ----------------------------------------------------------------
def to_csv(rows: list[dict[str, Any]], anonymise: bool = False) -> bytes:
    return rows_to_csv(rows, anonymise=anonymise).encode("utf-8")


def to_excel(rows: list[dict[str, Any]], anonymise: bool = False) -> bytes:
    frame = pd.DataFrame(flat_rows(rows, anonymise=anonymise), columns=columns())
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="results")
    return buf.getvalue()


# --- answers and roster (previously only reachable inside a report) ---------
ANSWER_COLUMNS = ["year", "hold", "group", "question_id", "question", "answer", "updated_at"]
ROSTER_COLUMNS = ["year", "hold", "group", "kuid", "display_name", "registered_at"]


def answer_rows(session, cohort_id: Optional[int] = None) -> list[dict[str, Any]]:
    """Free-text answers with their identity context and the question they answer."""
    from .exercise_bridge import content_sections
    from .models import Answer, Cohort, Group

    prompts = {q["id"]: q["prompt"] for q in content_sections()[1]}
    query = (session.query(Answer, Group, Cohort)
             .join(Group, Answer.group_id == Group.id)
             .join(Cohort, Group.cohort_id == Cohort.id))
    if cohort_id is not None:
        query = query.filter(Cohort.id == cohort_id)
    out = []
    for answer, group, cohort in query.order_by(Cohort.created_at, Group.name, Answer.question_id):
        out.append({
            "year": cohort.label, "hold": group.hold, "group": group.name,
            "question_id": answer.question_id,
            "question": prompts.get(answer.question_id, ""),
            "answer": answer.text,
            "updated_at": answer.updated_at.isoformat() if answer.updated_at else None,
        })
    return out


def roster_rows(session, cohort_id: Optional[int] = None) -> list[dict[str, Any]]:
    """Who was registered, in which group and hold — the thing a teacher needs for grading."""
    from .models import Cohort, Group, Member

    query = (session.query(Member, Group, Cohort)
             .join(Group, Member.group_id == Group.id)
             .join(Cohort, Group.cohort_id == Cohort.id))
    if cohort_id is not None:
        query = query.filter(Cohort.id == cohort_id)
    out = []
    for member, group, cohort in query.order_by(Cohort.created_at, Group.name, Member.kuid):
        out.append({
            "year": cohort.label, "hold": group.hold, "group": group.name,
            "kuid": member.kuid, "display_name": member.display_name,
            "registered_at": member.created_at.isoformat() if member.created_at else None,
        })
    return out


def to_answers_csv(session, cohort_id: Optional[int] = None) -> bytes:
    frame = pd.DataFrame(answer_rows(session, cohort_id), columns=ANSWER_COLUMNS)
    return frame.to_csv(index=False).encode("utf-8")


def build_workbook(session, rows: list[dict[str, Any]], cohort_id: Optional[int] = None,
                   include_events: bool = True) -> bytes:
    """One Excel file with everything a teacher needs: results, answers, roster, years, log.

    §B5's premise is that apps get retired and the export is what people keep — a single-sheet
    results file leaves the free-text answers and the roster stranded inside a PDF.
    """
    from . import events as events_mod
    from .cohorts import list_cohorts

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(flat_rows(rows), columns=columns()).to_excel(
            writer, index=False, sheet_name="results")
        pd.DataFrame(answer_rows(session, cohort_id), columns=ANSWER_COLUMNS).to_excel(
            writer, index=False, sheet_name="answers")
        pd.DataFrame(roster_rows(session, cohort_id), columns=ROSTER_COLUMNS).to_excel(
            writer, index=False, sheet_name="roster")
        pd.DataFrame(list_cohorts(session)).to_excel(writer, index=False, sheet_name="years")
        if include_events:
            pd.DataFrame(events_mod.recent(session, limit=5000)).to_excel(
                writer, index=False, sheet_name="log")
    return buf.getvalue()


def backup_sqlite() -> bytes:
    """A consistent snapshot of the database file (safe to take while the app is running).

    Uses SQLite's backup API rather than reading the file: with WAL enabled a raw copy can
    miss committed transactions still in the -wal file.
    """
    import sqlite3
    import tempfile
    from pathlib import Path

    from .config import settings

    source = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            target_path = Path(tmp) / "backup.sqlite"
            target = sqlite3.connect(target_path)
            try:
                source.backup(target)
            finally:
                target.close()
            return target_path.read_bytes()
    finally:
        source.close()


# --- plot rendering ---------------------------------------------------------
def figure_png(fig: Figure) -> Optional[bytes]:
    """Static PNG via kaleido; None if unavailable (report degrades gracefully)."""
    try:
        return fig.to_image(format="png", width=760, height=440, scale=2)
    except Exception:
        return None


def _figure_html(fig: Figure, include_js: bool) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=("cdn" if include_js else False))


# --- HTML report ------------------------------------------------------------
def build_html_report(ctx: ReportContext) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    data_df = pd.DataFrame(flat_rows(ctx.rows), columns=columns())
    css = f"""
      body {{ font-family: {theme.FONT_STACK}; color: {theme.CHARCOAL};
              background: {theme.SOFT_WHITE}; line-height: 1.6; margin: 24px; }}
      h1,h2,h3 {{ color: {theme.FOREST}; }}
      .card {{ background: {theme.IVORY}; border: 1px solid {theme.MINT};
               border-radius: 6px; padding: 14px 16px; margin: 14px 0; }}
      table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
      th {{ background: {theme.MINT}; color: {theme.CHARCOAL}; text-align: left; padding: 6px 8px; }}
      td {{ padding: 6px 8px; border-bottom: 1px solid {theme.MINT}; }}
      tr:nth-child(even) td {{ background: {theme.IVORY}; }}
      pre {{ background: {theme.SOFT_WHITE}; border: 1px solid {theme.MINT}; padding: 10px;
             overflow-x: auto; font-family: {theme.FONT_STACK}; }}
    """
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(ctx.title)}</title>",
             f"<style>{css}</style></head><body>"]
    parts.append(f"<h1>{html.escape(ctx.title)}</h1>")
    meta = f"{html.escape(ctx.course)} · {html.escape(ctx.group)} · hold {ctx.hold} · {html.escape(ctx.year)}"
    parts.append(f"<div class='card'>{meta}<br>Members: {html.escape(', '.join(ctx.members))}"
                 f"<br>Generated {now}</div>")

    parts.append("<h2>Captured data</h2>")
    parts.append(f"<div class='card'>{data_df.to_html(index=False, border=0)}</div>")

    if ctx.answers:
        parts.append("<h2>Answers</h2>")
        for a in ctx.answers:
            parts.append(f"<div class='card'><strong>{html.escape(a.get('prompt', ''))}</strong>"
                         f"<p>{html.escape(a.get('text', '') or '—')}</p></div>")

    if ctx.plots:
        parts.append("<h2>Plots</h2>")
        for i, plot in enumerate(ctx.plots):
            parts.append(f"<h3>{html.escape(plot.title)}</h3>")
            parts.append(_figure_html(plot.figure, include_js=(i == 0)))
            if plot.code:
                parts.append(f"<details><summary>Show the code</summary><pre>{html.escape(plot.code)}</pre></details>")

    # Quiet brand footer: the report is the thing students keep after the app is retired,
    # so it should still say where it came from.
    logo = theme.logo_uri(prefer_mark=False)
    logo_img = (f"<img src='{logo}' alt='CPDSE' height='40' "
                f"style='height:40px;width:auto;opacity:.9'>") if logo else ""
    parts.append(
        f"<hr style='border:none;border-top:1px solid {theme.MINT};margin-top:28px'>"
        f"<div style='display:flex;align-items:center;gap:12px;opacity:.8;font-size:.8rem'>"
        f"{logo_img}<span>Generated by {html.escape(ctx.course or ctx.title)} · {now}</span></div>")
    parts.append("</body></html>")
    return "".join(parts)


# --- PDF report -------------------------------------------------------------
def build_pdf_report(ctx: ReportContext) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title=ctx.title)
    styles = getSampleStyleSheet()
    forest = colors.HexColor(theme.FOREST)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", textColor=forest)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", textColor=forest)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", leading=14)
    mono = ParagraphStyle("mono", parent=styles["Code"], fontName="Courier", fontSize=7, leading=8)

    story: list[Any] = [Paragraph(html.escape(ctx.title), h1)]
    story.append(Paragraph(f"{html.escape(ctx.course)} &middot; {html.escape(ctx.group)} "
                           f"&middot; hold {ctx.hold} &middot; {html.escape(ctx.year)}", body))
    story.append(Paragraph("Members: " + html.escape(", ".join(ctx.members)), body))
    story.append(Spacer(1, 8))

    data = flat_rows(ctx.rows)
    story.append(Paragraph("Captured data", h2))
    if data:
        table_cols = columns()
        table_data = [table_cols] + [[str(row.get(c, "")) for c in table_cols] for row in data]
        tbl = Table(table_data, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(theme.MINT)),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(theme.CHARCOAL)),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(theme.MINT)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(theme.IVORY)]),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("No data captured yet.", body))
    story.append(Spacer(1, 8))

    if ctx.answers:
        story.append(Paragraph("Answers", h2))
        for a in ctx.answers:
            story.append(Paragraph("<b>" + html.escape(a.get("prompt", "")) + "</b>", body))
            story.append(Paragraph(html.escape(a.get("text", "") or "—"), body))
            story.append(Spacer(1, 4))

    if ctx.plots:
        story.append(Paragraph("Plots", h2))
        for plot in ctx.plots:
            story.append(Paragraph(html.escape(plot.title), body))
            png = figure_png(plot.figure)
            if png:
                story.append(Image(io.BytesIO(png), width=150 * mm, height=87 * mm))
            else:
                story.append(Paragraph("(interactive plot — see the HTML report)", body))
            if plot.code:
                story.append(Paragraph("Show the code:", body))
                for ln in plot.code.splitlines():
                    story.append(Paragraph(html.escape(ln).replace(" ", "&nbsp;") or "&nbsp;", mono))
            story.append(Spacer(1, 8))

    doc.build(story)
    return buf.getvalue()
