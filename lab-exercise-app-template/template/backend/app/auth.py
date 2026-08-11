"""Admin session auth (spec §8) — CHASSIS.

* The admin password is compared **constant-time** against ``ADMIN_PASSWORD``.
* On success a **signed, HTTP-only** session cookie is set. The signing secret is derived
  at startup (``config.settings.session_secret``) and never stored on disk, so rotation =
  redeploy. There is no password in any URL and no password on disk.
* If ``ADMIN_PASSWORD`` is unset the admin area is **disabled** — every guarded route and
  the password check fail closed, and the UI is told so via ``/api/meta``.
"""
from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from .config import settings

COOKIE_NAME = "admin_session"
SESSION_MAX_AGE = 8 * 60 * 60  # 8 hours
_SESSION_VALUE = "admin"

_signer = TimestampSigner(settings.session_secret)


def verify_password(candidate: str) -> bool:
    """Constant-time password check. Fails closed when admin is disabled."""
    if not settings.admin_enabled or settings.admin_password is None:
        return False
    return hmac.compare_digest(candidate.encode("utf-8"),
                               settings.admin_password.encode("utf-8"))


def issue_session(response: Response) -> None:
    token = _signer.sign(_SESSION_VALUE.encode("utf-8")).decode("utf-8")
    # Path "/" — AdaLab strips the /apps/<slug>/ prefix before the backend sees the request,
    # so the backend can't scope the cookie to the prefix; "/" is sent on every request the
    # proxy forwards to this app.
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # served over http locally / behind the AdaLab proxy
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def _valid_session(token: str | None) -> bool:
    if not token:
        return False
    try:
        _signer.unsign(token, max_age=SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def is_admin(request: Request) -> bool:
    """Non-raising check — used by the export route to gate full-history/Parquet."""
    return settings.admin_enabled and _valid_session(request.cookies.get(COOKIE_NAME))


def require_admin(request: Request) -> None:
    """FastAPI dependency guarding every ``/api/admin/*`` route."""
    if not settings.admin_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The admin area is disabled because ADMIN_PASSWORD is not set.",
        )
    if not _valid_session(request.cookies.get(COOKIE_NAME)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required.",
        )


AdminGuard = Depends(require_admin)
