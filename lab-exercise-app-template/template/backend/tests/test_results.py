"""Append-only results & supersede semantics (§5, §15.3, §15.10)."""
from __future__ import annotations

from tests.conftest import valid_measurement


def _group(client):
    return client.post("/api/groups", json={"name": "G", "members": ["Ana"]}).json()


def test_submit_appears_in_latest(client):
    g = _group(client)
    r = client.post(f"/api/groups/{g['id']}/results", json=valid_measurement(absorbance_au=0.5))
    assert r.status_code == 201
    latest = client.get("/api/results?cohort=all&latest=true").json()
    assert len(latest) == 1
    assert latest[0]["values"]["absorbance_au"] == 0.5
    assert latest[0]["superseded"] is False


def test_supersede_keeps_history_shows_latest(client):
    g = _group(client)
    first = client.post(f"/api/groups/{g['id']}/results",
                        json=valid_measurement(absorbance_au=0.5)).json()
    corrected = client.post(f"/api/results/{first['id']}/supersede",
                            json=valid_measurement(absorbance_au=0.7))
    assert corrected.status_code == 201

    latest = client.get("/api/results?latest=true").json()
    assert len(latest) == 1 and latest[0]["values"]["absorbance_au"] == 0.7

    history = client.get("/api/results?latest=false").json()
    assert len(history) == 2
    old = next(r for r in history if r["id"] == first["id"])
    new = next(r for r in history if r["id"] == corrected.json()["id"])
    assert old["superseded"] is True and old["superseded_by"] == new["id"]
    assert new["superseded"] is False


def test_cannot_supersede_twice(client):
    g = _group(client)
    first = client.post(f"/api/groups/{g['id']}/results", json=valid_measurement()).json()
    client.post(f"/api/results/{first['id']}/supersede", json=valid_measurement())
    again = client.post(f"/api/results/{first['id']}/supersede", json=valid_measurement())
    assert again.status_code == 409


def test_invalid_payload_rejected_422(client):
    g = _group(client)
    assert client.post(f"/api/groups/{g['id']}/results",
                       json=valid_measurement(absorbance_au=-1)).status_code == 422
    assert client.post(f"/api/groups/{g['id']}/results",
                       json=valid_measurement(replicate=0)).status_code == 422
    bad = valid_measurement()
    del bad["buffer"]
    assert client.post(f"/api/groups/{g['id']}/results", json=bad).status_code == 422
    assert client.post(f"/api/groups/{g['id']}/results",
                       json=valid_measurement(buffer="NotABuffer")).status_code == 422


def test_hard_delete_requires_admin(client):
    g = _group(client)
    res = client.post(f"/api/groups/{g['id']}/results", json=valid_measurement()).json()
    # A student (no admin session) cannot hard-delete.
    assert client.delete(f"/api/admin/results/{res['id']}").status_code == 401
    # ...and the row is untouched.
    assert len(client.get("/api/results?latest=false").json()) == 1


def test_hard_delete_admin_and_audited(admin_client):
    g = _group(admin_client)
    res = admin_client.post(f"/api/groups/{g['id']}/results", json=valid_measurement()).json()
    # Admin hard-deletes a single bogus row (the only destructive path).
    assert admin_client.delete(f"/api/admin/results/{res['id']}").status_code == 200
    assert admin_client.get("/api/results?latest=false").json() == []
    audit = admin_client.get("/api/admin/audit").json()
    assert any(a["action"] == "result_hard_delete" for a in audit)
