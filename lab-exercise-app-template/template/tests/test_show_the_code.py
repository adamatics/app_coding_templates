"""LOAD-BEARING (§B7, §B10): every plot's "Show the code" must run standalone.

The snippet is executed in a **fresh subprocess** whose working directory contains only an
exported CSV — no app code, no streamlit, no test fixtures on the path. That is the exact
situation of a student pasting it into a notebook next to their downloaded data.
"""
from __future__ import annotations

import ast
import subprocess
import sys

import pytest

from core import analysis, export, plots
from core import results as R
from exercise import analysis as seam_analysis
from tests.conftest import register_student, valid_measurement

COMPOUNDS = ["aspirin", "caffeine", "ibuprofen", "paracetamol"]


def _seed(session, n: int = 4):
    m = register_student(session)
    for i in range(n):
        R.submit_result(session, m.id, valid_measurement(
            compound_name=COMPOUNDS[i % len(COMPOUNDS)],
            measured_logp=1.0 + i * 0.4, database_logp=1.1 + i * 0.35,
            tool_logp=1.2 + i * 0.3, replicate=i + 1))
    return m


def _run_snippet(code: str, csv_text: str, tmp_path) -> subprocess.CompletedProcess:
    """Run the snippet in a clean dir containing only results.csv (no app code importable)."""
    (tmp_path / "results.csv").write_text(csv_text, encoding="utf-8")
    # fig.show() would try to open a browser; stub it to a no-op render.
    script = code.replace("fig.show()", "print('FIGURE_OK', type(fig).__name__)")
    (tmp_path / "snippet.py").write_text(script, encoding="utf-8")
    return subprocess.run([sys.executable, "snippet.py"], cwd=str(tmp_path),
                          capture_output=True, text=True, timeout=180)


def test_snippets_are_valid_python_and_not_streamlit(session):
    _seed(session)
    rows = R.query_results(session)
    df = analysis.to_dataframe(rows, anonymise=False)
    for fig, code in [
        plots.scatter(df, x="database_logp", y="measured_logp"),
        plots.histogram(df, x="measured_logp"),
        plots.box(df, x="year", y="measured_logp"),
        plots.bar(df, x="compound_name", y="measured_logp"),
        plots.line(df, x="replicate", y="measured_logp"),
    ]:
        ast.parse(code)                       # valid Python
        assert "streamlit" not in code        # never Streamlit-specific (§B7)
        assert "import pandas as pd" in code and "import plotly.express as px" in code
        assert "pd.read_csv" in code          # reads the exported CSV


def test_every_reference_plot_code_runs_standalone(session, tmp_path):
    """Each plot the reference app shows must reproduce from the exported CSV alone."""
    _seed(session)
    rows = R.query_results(session)
    csv_text = export.to_csv(rows).decode("utf-8")
    own_df = analysis.to_dataframe(rows, anonymise=False)
    compare_df = analysis.to_dataframe(rows, anonymise=True)

    built = seam_analysis.build_plots(own_df, compare_df, source="results.csv")
    assert built, "the reference exercise should produce plots"

    for plot in built:
        proc = _run_snippet(plot["code"], csv_text, tmp_path)
        assert proc.returncode == 0, (
            f"'Show the code' for {plot['title']!r} failed standalone:\n"
            f"--- code ---\n{plot['code']}\n--- stderr ---\n{proc.stderr}")
        assert "FIGURE_OK" in proc.stdout


def test_snippet_reads_the_exported_csv_columns(session, tmp_path):
    """The snippet's column references must exist in the exported CSV (no drift)."""
    _seed(session)
    rows = R.query_results(session)
    csv_text = export.to_csv(rows).decode("utf-8")
    header = csv_text.splitlines()[0].split(",")
    df = analysis.to_dataframe(rows, anonymise=False)
    _, code = plots.scatter(df, x="database_logp", y="measured_logp", color="method")
    for col in ("database_logp", "measured_logp", "method"):
        assert col in header, f"snippet references {col}, missing from the export"
    proc = _run_snippet(code, csv_text, tmp_path)
    assert proc.returncode == 0, proc.stderr
