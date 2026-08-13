"""Plot helpers that emit their own source (§B7). CHASSIS, framework-free (no streamlit).

Each helper returns ``(figure, code_str)``. ``code_str`` is plain pandas + plotly a student
can paste into a notebook — it reads an exported CSV and reproduces the SAME plot. It is
never Streamlit-specific and, being generated from the same call, never drifts from what the
app drew. The chassis renders it in a "Show the code" expander under every plot.
"""
from __future__ import annotations

from typing import Any, Optional

import plotly.express as px
from plotly.graph_objs import Figure

from .theme import CPDSE_SEQUENCE, plotly_template

_TEMPLATE = plotly_template()
_SEQ_LITERAL = repr(CPDSE_SEQUENCE)  # embedded verbatim so the snippet is self-contained


def _style(fig: Figure, title: Optional[str]) -> Figure:
    fig.update_layout(template=_TEMPLATE, margin=dict(l=40, r=20, t=50 if title else 20, b=40))
    if title:
        fig.update_layout(title=title)
    return fig


def _kwargs_repr(kwargs: dict[str, Any]) -> str:
    parts = []
    for key, value in kwargs.items():
        if value is None:
            continue
        parts.append(f"{key}={value!r}")
    return ", ".join(parts)


def _emit(func: str, source: str, kwargs: dict[str, Any]) -> str:
    """Build the standalone notebook snippet that reproduces the figure from ``source``."""
    call_kwargs = _kwargs_repr(kwargs)
    sep = ", " if call_kwargs else ""
    call = f"px.{func}(df{sep}{call_kwargs}, color_discrete_sequence=CPDSE)"
    return (
        "import pandas as pd\n"
        "import plotly.express as px\n\n"
        f"CPDSE = {_SEQ_LITERAL}\n"
        f"df = pd.read_csv({source!r})\n"
        f"fig = {call}\n"
        "fig.show()\n"
    )


def _make(func: str, df, source: str, title: Optional[str], **kwargs) -> tuple[Figure, str]:
    px_func = getattr(px, func)
    fig = px_func(df, color_discrete_sequence=CPDSE_SEQUENCE,
                  **{k: v for k, v in kwargs.items() if v is not None})
    code = _emit(func, source, kwargs)
    return _style(fig, title), code


# --- public helpers (df is a pandas DataFrame; source is the exported CSV name) ---
def scatter(df, x: str, y: str, color: Optional[str] = None, title: Optional[str] = None,
            source: str = "results.csv") -> tuple[Figure, str]:
    return _make("scatter", df, source, title, x=x, y=y, color=color)


def line(df, x: str, y: str, color: Optional[str] = None, title: Optional[str] = None,
         source: str = "results.csv") -> tuple[Figure, str]:
    return _make("line", df, source, title, x=x, y=y, color=color)


def histogram(df, x: str, color: Optional[str] = None, nbins: Optional[int] = None,
              title: Optional[str] = None, source: str = "results.csv") -> tuple[Figure, str]:
    return _make("histogram", df, source, title, x=x, color=color, nbins=nbins)


def box(df, x: Optional[str], y: str, color: Optional[str] = None, title: Optional[str] = None,
        source: str = "results.csv") -> tuple[Figure, str]:
    return _make("box", df, source, title, x=x, y=y, color=color)


def bar(df, x: str, y: str, color: Optional[str] = None, title: Optional[str] = None,
        source: str = "results.csv") -> tuple[Figure, str]:
    return _make("bar", df, source, title, x=x, y=y, color=color)
