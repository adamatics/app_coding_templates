"""URL-token plumbing for durable sessions (CHASSIS, Streamlit layer).

``core/sessions.py`` owns the tokens; this module is the thin Streamlit half that reads and
writes the ``?s=`` query parameter. Kept out of ``core/`` so ``core/`` stays framework-free.
"""
from __future__ import annotations

from typing import Optional

import streamlit as st

PARAM = "s"


def read_session_token() -> Optional[str]:
    try:
        value = st.query_params.get(PARAM)
    except Exception:  # pragma: no cover - very old Streamlit without query_params
        return None
    if isinstance(value, list):  # some versions hand back a list
        value = value[0] if value else None
    return value or None


def remember_session_token(token: str) -> None:
    """Put the token in the URL so a refresh or a new tab keeps the session."""
    if not token:
        return
    try:
        if read_session_token() != token:
            st.query_params[PARAM] = token
    except Exception:  # pragma: no cover
        pass


def clear_session_token() -> None:
    try:
        if PARAM in st.query_params:
            del st.query_params[PARAM]
    except Exception:  # pragma: no cover
        pass
