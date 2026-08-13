"""Shared chassis UI components carrying the CPDSE identity (§13). Streamlit layer.

Exercise pages compose these rather than styling from scratch (.claude/rules), so the identity
holds across apps. Colours come only from ``core.theme`` (the single hex source). We avoid
Streamlit's built-in ``st.error``/``success``/``info``/``warning`` because they render off-palette
red/green/blue/amber; use ``notice`` instead (the palette has no red/amber — §13).
"""
from __future__ import annotations

from typing import Optional

import streamlit as st

from core import theme

def _logo_img(height_px: int, prefer_mark: bool = True, opacity: float = 1.0) -> str:
    """<img> for the CPDSE artwork, or empty string when no asset has been supplied.

    The logo is forest-green on transparent, so on the dark header band it sits inside a
    small ivory chip — the brand colours stay correct rather than being recoloured.
    """
    uri = theme.logo_uri(prefer_mark=prefer_mark)
    if not uri:
        return ""
    return (f"<img src='{uri}' alt='CPDSE' height='{height_px}' "
            f"style='height:{height_px}px;width:auto;display:block;opacity:{opacity}'>")


def inject_theme() -> None:
    """Global CSS: Verdana everywhere, CPDSE buttons/links, remove off-palette accents."""
    st.markdown(f"""
    <style>
      html, body, [class*="css"], .stApp, button, input, textarea, select {{
        font-family: {theme.FONT_STACK} !important;
      }}
      .stApp {{ background: {theme.SOFT_WHITE}; color: {theme.CHARCOAL}; }}
      h1, h2, h3 {{ color: {theme.FOREST}; font-weight: 700; }}
      a {{ color: {theme.FOREST}; }}
      /* primary buttons: Antique Gold fill, Forest ink (approved pair) */
      .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
        background: {theme.GOLD}; color: {theme.FOREST}; border: 1px solid {theme.GOLD};
        font-weight: 700; border-radius: 6px;
      }}
      .stButton > button:hover, .stFormSubmitButton > button:hover {{
        background: {theme.SAND}; color: {theme.FOREST}; border-color: {theme.SAND};
      }}
      .cpdse-header {{ background: {theme.FOREST}; padding: 12px 18px; border-radius: 6px;
        display: flex; align-items: center; gap: 16px; margin-bottom: 12px; }}
      .cpdse-header .title {{ color: {theme.SOFT_WHITE}; font-size: 1.15rem; font-weight: 700; }}
      /* The logo is Forest Green on transparent; on the Forest band it needs a light chip
         behind it. Ivory Gold Tint on Forest keeps both inside the CPDSE palette. */
      .cpdse-logo-chip {{ background: {theme.IVORY}; border-radius: 8px; padding: 5px 7px;
        display: inline-flex; align-items: center; flex: 0 0 auto; }}
      .cpdse-header .code {{ color: {theme.SAND}; font-weight: 400; }}
      .cpdse-card {{ background: {theme.IVORY}; border: 1px solid {theme.MINT};
        border-radius: 6px; padding: 12px 14px; margin: 10px 0; }}
      .cpdse-notice {{ background: {theme.IVORY}; border: 1px solid {theme.MINT};
        border-left: 5px solid {theme.GOLD}; border-radius: 6px; padding: 10px 12px; margin: 8px 0; }}
      .cpdse-notice.err {{ border-left-color: {theme.CHARCOAL}; border-width: 1px 1px 1px 5px; font-weight: 700; }}
      .cpdse-notice.ok {{ border-left-color: {theme.FOREST}; }}
    </style>
    """, unsafe_allow_html=True)


def header(title: str, course_code: str = "") -> None:
    """The Forest band. The exercise title is the hero; the logo is a quiet anchor beside it."""
    code = f"<span class='code'>· {course_code}</span>" if course_code else ""
    logo = _logo_img(30, prefer_mark=True)
    chip = f"<span class='cpdse-logo-chip'>{logo}</span>" if logo else ""
    st.markdown(
        f"<div class='cpdse-header'>{chip}<span class='title'>{title} {code}</span></div>",
        unsafe_allow_html=True,
    )


def signin_logo() -> None:
    """The full lock-up, centred, on the sign-in page — the one place it gets room."""
    logo = _logo_img(132, prefer_mark=False)
    if logo:
        st.markdown(
            f"<div style='display:flex;justify-content:center;margin:8px 0 4px'>{logo}</div>",
            unsafe_allow_html=True)


def banner(text: str) -> None:
    if text and text.strip():
        st.markdown(f"<div class='cpdse-notice'>📣 {text}</div>", unsafe_allow_html=True)


def notice(text: str, tone: str = "info") -> None:
    """Palette-correct message. tone: info | err | ok (never red/amber)."""
    cls = {"info": "", "err": " err", "ok": " ok"}.get(tone, "")
    st.markdown(f"<div class='cpdse-notice{cls}'>{text}</div>", unsafe_allow_html=True)


def show_the_code(figure, code: str, caption: Optional[str] = None) -> None:
    """Render a plot with an expandable 'Show the code' panel (§B7)."""
    st.plotly_chart(figure, use_container_width=True)
    if caption:
        st.caption(caption)
    with st.expander("Show the code"):
        st.caption("Plain pandas + plotly — paste into a notebook, run against your exported CSV.")
        st.code(code, language="python")


def footer(institution_name: str, contact_email: str) -> None:
    st.markdown("---")
    st.caption(f"{institution_name} · {contact_email} · A safe space to learn data science.")
