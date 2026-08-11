"""Admin group/member management preserves history (spec §8, priority: data durability)."""
from __future__ import annotations

from tests.conftest import DEFAULT_COHORT, valid_measurement


def _group(client, name):
    return client.post("/api/groups", json={"name": name, "members": ["Ana"]}).json()


def test_rename_group_and_conflict(admin_client):
    g = _group(admin_client, "Alpha")
    _group(admin_client, "Beta")
    assert admin_client.patch(f"/api/admin/groups/{g['id']}", json={"name": "Gamma"}).status_code == 200
    # renaming onto an existing name is a clean 409
    assert admin_client.patch(f"/api/admin/groups/{g['id']}", json={"name": "Beta"}).status_code == 409


def test_merge_reparents_results_history_preserved(admin_client):
    a = _group(admin_client, "Alpha")
    b = _group(admin_client, "Beta")
    admin_client.post(f"/api/groups/{a['id']}/results", json=valid_measurement(absorbance_au=0.1))
    admin_client.post(f"/api/groups/{b['id']}/results", json=valid_measurement(absorbance_au=0.2))
    # merge Alpha into Beta
    assert admin_client.post("/api/admin/groups/merge",
                             json={"source_id": a["id"], "target_id": b["id"]}).status_code == 200
    # Both results survive, now under Beta — nothing destroyed.
    rows = admin_client.get("/api/results?cohort=all&latest=false").json()
    assert len(rows) == 2
    assert {r["group"] for r in rows} == {"Beta"}
    # Alpha is gone from the cohort's groups.
    groups = admin_client.get(f"/api/admin/groups?cohort={DEFAULT_COHORT}").json()
    assert "Alpha" not in {g["name"] for g in groups}


def test_delete_group_refused_when_it_has_results(admin_client):
    a = _group(admin_client, "Alpha")
    admin_client.post(f"/api/groups/{a['id']}/results", json=valid_measurement())
    # Deleting a group with data is refused (use merge) — history is never dropped.
    resp = admin_client.delete(f"/api/admin/groups/{a['id']}")
    assert resp.status_code == 409
    assert "merge" in resp.json()["detail"].lower()


def test_delete_empty_group_and_member(admin_client):
    a = _group(admin_client, "Alpha")  # has one member "Ana"
    member_id = admin_client.get(f"/api/admin/groups?cohort={DEFAULT_COHORT}").json()[0]["members"][0]["id"]
    assert admin_client.delete(f"/api/admin/members/{member_id}").status_code == 200
    # now empty -> deletable
    assert admin_client.delete(f"/api/admin/groups/{a['id']}").status_code == 200
