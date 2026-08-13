"""Durable sessions in the browser (CHASSIS, Streamlit layer).

``core/sessions.py`` owns the tokens; this module is the thin Streamlit half that keeps one in
the browser, so a student who has signed in once does not have to do it again.

**Why there are two places to keep it.** The token started life in the URL alone (``?s=…``).
That survives a refresh and the back button, because the query string travels with them — but
it does *not* survive the thing students actually do: opening the app again from the AdaLab
gallery, a bookmark, or a link in the course notes. Those all load the **bare** URL, the token
is absent, and the student is asked for the course password and to register all over again —
creating a duplicate registration each time.

So the token is now kept in a **cookie** as well:

* **Write** — a cookie cannot be set from Python, so a tiny inline script sets it in the
  browser. It runs only when the browser's copy differs from the current token, which in
  practice means once per sign-in rather than once per rerun.
* **Read** — ``st.context.cookies`` exposes the request's cookies server-side, so the next
  visit restores the session before anything renders. No redirect, no flash.

The URL parameter stays, for three reasons: it costs nothing, it still works if cookies are
blocked, and a student who copies the URL from their own address bar into another browser
keeps their place.

**The cookie name is per app** (`session_<slug>`). Several CPDSE apps share one hostname, so a
shared name would sign a student into the wrong exercise.

**Failure is always soft.** Every browser interaction is wrapped: if cookies are blocked, an
old Streamlit lacks ``st.context``, or the component sandbox changes, the app falls back to the
URL parameter and, failing that, to asking for the course password — the behaviour before this
existed. Nothing here is allowed to stop a student working.
"""
from __future__ import annotations

import json
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from core.config import settings

PARAM = "s"


def _cookie_name() -> str:
    """Per-app, because several course apps are served from one hostname."""
    slug = (settings.project_slug or "app").replace("-", "_")
    return f"session_{slug}"


# --- reading ----------------------------------------------------------------
def _from_url() -> Optional[str]:
    try:
        value = st.query_params.get(PARAM)
    except Exception:  # pragma: no cover - very old Streamlit without query_params
        return None
    if isinstance(value, list):  # some versions hand back a list
        value = value[0] if value else None
    return value or None


def _from_cookie() -> Optional[str]:
    try:
        return st.context.cookies.get(_cookie_name()) or None
    except Exception:  # pragma: no cover - no st.context, or cookies unavailable
        return None


def read_session_token() -> Optional[str]:
    """The URL wins over the cookie: an explicit link is a deliberate act, a cookie is not.

    That ordering also makes "send me your link" work as a support tool — opening someone
    else's link uses their session rather than silently reverting to your own.

    The result is always a plain string or None. Both sources are outside our control — a
    query string is user input and the cookie jar depends on the Streamlit version — and
    ``core.sessions`` hashes whatever it is handed, so a stray dict or list would surface as
    an unreadable crash on the very first page.
    """
    for value in (_from_url(), _from_cookie()):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


# --- writing ----------------------------------------------------------------
def _run_script(script: str) -> None:
    """Run a snippet in the page. Height 0 so it takes no space.

    Streamlit renders components in an iframe, so this reaches for the parent document and
    falls back to its own if that is blocked. Both paths are wrapped in try/catch: a browser
    that refuses cookies must not break the app, it just means signing in again next visit.
    """
    components.html(
        f"<script>try{{{script}}}catch(e){{}}</script>",
        height=0, width=0,
    )


def remember_session_token(token: str) -> None:
    """Keep the token in the URL and in a cookie, so any way back into the app works."""
    if not token:
        return
    try:
        if _from_url() != token:
            st.query_params[PARAM] = token
    except Exception:  # pragma: no cover
        pass

    # Only touch the browser when its copy is actually out of date — otherwise this would
    # inject a script element on every single rerun.
    if _from_cookie() == token:
        return

    max_age = max(1, int(settings.session_ttl_days)) * 24 * 60 * 60
    _run_script(
        f"var d=(window.parent&&window.parent.document)||document;"
        f"var s=(d.location&&d.location.protocol==='https:')?';Secure':'';"
        f"d.cookie={json.dumps(_cookie_name())}+'='+{json.dumps(token)}"
        f"+';max-age={max_age};path=/;SameSite=Lax'+s;"
    )


def clear_session_token() -> None:
    """Sign out properly: the URL and the cookie both have to go."""
    try:
        if PARAM in st.query_params:
            del st.query_params[PARAM]
    except Exception:  # pragma: no cover
        pass

    if _from_cookie() is None:
        return
    _run_script(
        f"var d=(window.parent&&window.parent.document)||document;"
        f"d.cookie={json.dumps(_cookie_name())}+'=;max-age=0;path=/;SameSite=Lax';"
    )
