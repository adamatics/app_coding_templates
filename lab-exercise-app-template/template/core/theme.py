"""CPDSE visual identity — the single source of colour (spec §13). CHASSIS, no streamlit.

This is the ONLY module permitted to contain raw hex. Everything else (the plotly template,
the Streamlit CSS in pages/_components.py, the reports) reads these constants. Values are
verbatim from https://cpdse.dk/visual-identity/. Do not invent an error red/amber — the
palette has none; convey state with words and weight (§13).
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
from typing import Optional

import plotly.graph_objects as go

# --- brand assets -----------------------------------------------------------
# Artwork lives in assets/ at the app root. Drop the official files in; nothing here needs
# editing. SVG is preferred, raster accepted — see assets/README.md.
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_IMAGE_SUFFIXES = (".svg", ".png", ".webp", ".jpg", ".jpeg")
_MIME = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp",
         ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


@lru_cache(maxsize=8)
def asset_path(basename: str) -> Optional[Path]:
    """First existing ``assets/<basename>.<ext>``, preferring SVG. None if absent."""
    for suffix in _IMAGE_SUFFIXES:
        candidate = ASSETS_DIR / f"{basename}{suffix}"
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=8)
def asset_data_uri(basename: str) -> Optional[str]:
    """A ``data:`` URI for the asset, safe to drop straight into an <img src>.

    Inlining keeps the logo working with no static-file route, in the PDF/HTML reports, and
    under any URL prefix. The files are small, and results are cached per process.
    """
    path = asset_path(basename)
    if path is None:
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    mime = _MIME.get(path.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def logo_uri(prefer_mark: bool = False) -> Optional[str]:
    """The brand image to display.

    ``prefer_mark=True`` asks for the text-free mark (header, small sizes) and falls back to
    the full lock-up when only one file has been supplied — so dropping in a single logo is
    enough to brand the whole app.
    """
    order = ("cpdse-mark", "cpdse-logo") if prefer_mark else ("cpdse-logo", "cpdse-mark")
    for name in order:
        uri = asset_data_uri(name)
        if uri:
            return uri
    return None

# --- palette ----------------------------------------------------------------
FOREST = "#3C5E3E"
SAGE = "#5F7D61"
MINT = "#A9BBAA"
GOLD = "#D6C17C"
SAND = "#E4D7A1"
IVORY = "#F6F1DC"
CHARCOAL = "#333333"
SOFT_WHITE = "#F9F9F9"  # never pure white (§13)

FONT_STACK = "Verdana, Geneva, 'DejaVu Sans', sans-serif"

# Sequential chart series order (§13): Forest, Antique Gold, Sage, Mint, Warm Sand.
CPDSE_SEQUENCE = [FOREST, GOLD, SAGE, MINT, SAND]


def plotly_template() -> go.layout.Template:
    """A plotly template applying the CPDSE identity to every figure."""
    return go.layout.Template(
        layout=dict(
            font=dict(family=FONT_STACK, color=CHARCOAL, size=13),
            colorway=CPDSE_SEQUENCE,
            paper_bgcolor=SOFT_WHITE,
            plot_bgcolor=SOFT_WHITE,
            title=dict(font=dict(family=FONT_STACK, color=FOREST, size=16)),
            xaxis=dict(gridcolor=MINT, zerolinecolor=MINT, linecolor=MINT),
            yaxis=dict(gridcolor=MINT, zerolinecolor=MINT, linecolor=MINT),
            legend=dict(font=dict(family=FONT_STACK, color=CHARCOAL)),
            colorscale=dict(sequential=[[0, IVORY], [1, FOREST]]),
        )
    )
