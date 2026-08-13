"""Export: four formats + CSV column stability across cohorts (§B5, §B10)."""
from __future__ import annotations

import io

import pandas as pd

from core import analysis, cohorts, export, plots
from core import results as R
from tests.conftest import DEFAULT_YEAR, SECOND_YEAR, register_student, valid_measurement

EXPECTED = R.columns()


def _seed(session, kuid="abc123", group="G1", **over):
    m = register_student(session, kuid, "Ana", 1, group)
    R.submit_result(session, m.id, valid_measurement(**over))
    return m


def test_csv_export_columns(session):
    _seed(session)
    text = export.to_csv(R.query_results(session)).decode("utf-8")
    assert text.splitlines()[0] == ",".join(EXPECTED)


def test_csv_columns_identical_across_two_cohorts(session):
    """§B10: CSV columns identical across two different cohorts of the same exercise."""
    _seed(session, "aaa111", "G1", measured_logp=1.0)
    header_first = export.to_csv(R.query_results(session)).decode("utf-8").splitlines()[0]

    cohorts.close_open_cohort(session)
    cohorts.create_cohort(session, SECOND_YEAR)
    _seed(session, "bbb222", "G1", measured_logp=3.0)   # same group name, new year
    rows_all = R.query_results(session)
    text_all = export.to_csv(rows_all).decode("utf-8")
    header_second = text_all.splitlines()[0]

    assert header_first == header_second == ",".join(EXPECTED)
    frame = pd.read_csv(io.StringIO(text_all))
    assert set(frame["year"].astype(str)) == {DEFAULT_YEAR, SECOND_YEAR}
    assert list(frame.columns) == EXPECTED  # directly concatenable


def test_excel_export_roundtrips(session):
    _seed(session)
    data = export.to_excel(R.query_results(session))
    frame = pd.read_excel(io.BytesIO(data))
    assert list(frame.columns) == EXPECTED and len(frame) == 1


def _report_ctx(session):
    rows = R.query_results(session)
    df = analysis.to_dataframe(rows, anonymise=False)
    fig, code = plots.scatter(df, x="database_logp", y="measured_logp", title="t")
    return export.ReportContext(
        title="logP report", course="Chem 101", year=DEFAULT_YEAR, hold=1, group="G1",
        members=["Ana"], rows=rows,
        answers=[{"prompt": "How well does it agree?", "text": "Quite well."}],
        plots=[export.ReportPlot(title="Measured vs database", figure=fig, code=code)],
    )


def test_html_report_contains_data_answers_and_code(session):
    _seed(session)
    html = export.build_html_report(_report_ctx(session))
    assert "logP report" in html
    assert "aspirin" in html                    # captured data
    assert "Quite well." in html                # free-text answers
    assert "Show the code" in html and "px.scatter" in html   # plot + its code
    assert "plotly" in html.lower()


def test_pdf_report_is_a_pdf(session):
    _seed(session)
    data = export.build_pdf_report(_report_ctx(session))
    assert data.startswith(b"%PDF"), "PDF report should be a real PDF"
    assert len(data) > 1500
