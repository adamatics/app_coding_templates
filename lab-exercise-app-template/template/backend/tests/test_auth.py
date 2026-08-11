"""Admin auth: constant-time compare, session cookie, fail-closed when unset (§8, §15.10)."""
from __future__ import annotations

from app import auth
from app.config import settings
from tests.conftest import ADMIN_PASSWORD


def test_wrong_password_rejected(client):
    resp = client.post("/api/admin/login", json={"password": "nope"})
    assert resp.status_code == 401


def test_correct_password_grants_session(client):
    resp = client.post("/api/admin/login", json={"password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    # Session cookie is set and guarded routes now work.
    assert client.get("/api/admin/session").status_code == 200


def test_guarded_route_requires_session(client):
    assert client.get("/api/admin/session").status_code == 401
    assert client.get("/api/admin/cohorts").status_code == 401


def test_logout_clears_session(admin_client):
    assert admin_client.get("/api/admin/session").status_code == 200
    admin_client.post("/api/admin/logout")
    assert admin_client.get("/api/admin/session").status_code == 401


def test_verify_password_constant_time_true_false():
    assert auth.verify_password(ADMIN_PASSWORD) is True
    assert auth.verify_password("wrong") is False


def test_fail_closed_when_admin_password_unset(client):
    original = settings.admin_password
    object.__setattr__(settings, "admin_password", None)
    try:
        assert settings.admin_enabled is False
        assert auth.verify_password("anything") is False
        # Login is forbidden and guarded routes 403 (disabled), not 401.
        assert client.post("/api/admin/login", json={"password": "x"}).status_code == 403
        assert client.get("/api/admin/session").status_code == 403
        # meta advertises the disabled state so the UI can say so.
        assert client.get("/api/meta").json()["admin_enabled"] is False
    finally:
        object.__setattr__(settings, "admin_password", original)
