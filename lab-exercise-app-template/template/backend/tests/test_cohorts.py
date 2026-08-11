"""Cohort lifecycle & durability: close-not-delete, closed rejects writes, one open (§5, §15.4)."""
from __future__ import annotations

from tests.conftest import DEFAULT_COHORT, SECOND_COHORT, valid_measurement


def _create_group(client, name="Team A"):
    return client.post("/api/groups", json={"name": name, "members": ["Ana"]}).json()


def test_default_cohort_is_open(client):
    assert client.get("/api/meta").json()["open_cohort"] == DEFAULT_COHORT


def test_close_makes_writes_rejected_then_reopen(admin_client):
    group = _create_group(admin_client)
    # A result can be submitted while open.
    assert admin_client.post(f"/api/groups/{group['id']}/results",
                             json=valid_measurement()).status_code == 201

    # Close the open cohort — this is the only "reset".
    resp = admin_client.post("/api/admin/cohorts/close")
    assert resp.status_code == 200 and resp.json()["status"] == "closed"

    # Writes to the now-closed cohort are rejected with a clear 409.
    r = admin_client.post(f"/api/groups/{group['id']}/results", json=valid_measurement())
    assert r.status_code == 409
    assert "closed" in r.json()["detail"].lower()
    assert admin_client.post("/api/groups", json={"name": "Late", "members": []}).status_code == 409

    # Open a new cohort; the old one is still visible and exportable.
    assert admin_client.post("/api/admin/cohorts", json={"label": SECOND_COHORT}).status_code == 201
    labels = {c["label"] for c in admin_client.get("/api/cohorts").json()}
    assert {DEFAULT_COHORT, SECOND_COHORT} <= labels
    # Old cohort's data still queryable via the compare view.
    all_results = admin_client.get("/api/results?cohort=all").json()
    assert any(r["cohort"] == DEFAULT_COHORT for r in all_results)


def test_cannot_open_second_cohort_while_one_open(admin_client):
    assert admin_client.post("/api/admin/cohorts", json={"label": "extra"}).status_code == 409


def test_duplicate_cohort_label_rejected(admin_client):
    admin_client.post("/api/admin/cohorts/close")
    assert admin_client.post("/api/admin/cohorts", json={"label": DEFAULT_COHORT}).status_code == 409


def test_close_when_none_open_is_conflict(admin_client):
    admin_client.post("/api/admin/cohorts/close")
    assert admin_client.post("/api/admin/cohorts/close").status_code == 409
