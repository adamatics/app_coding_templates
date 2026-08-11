"""Group naming rules: unique per cohort, case-insensitive, reusable across cohorts (§5)."""
from __future__ import annotations

from tests.conftest import SECOND_COHORT


def test_group_names_unique_case_insensitive(client):
    assert client.post("/api/groups", json={"name": "Team A", "members": []}).status_code == 201
    dup = client.post("/api/groups", json={"name": "team a", "members": []})
    assert dup.status_code == 409
    assert "already exists" in dup.json()["detail"].lower()


def test_same_name_allowed_in_different_cohort(admin_client):
    assert admin_client.post("/api/groups", json={"name": "Team A", "members": []}).status_code == 201
    admin_client.post("/api/admin/cohorts/close")
    admin_client.post("/api/admin/cohorts", json={"label": SECOND_COHORT})
    # Same name is fine in the new cohort.
    assert admin_client.post("/api/groups", json={"name": "Team A", "members": []}).status_code == 201


def test_create_group_with_members_and_append(client):
    group = client.post("/api/groups", json={"name": "G", "members": ["Ana", "Bo"]}).json()
    assert {m["display_name"] for m in group["members"]} == {"Ana", "Bo"}
    client.post(f"/api/groups/{group['id']}/members", json={"display_name": "Cy"})
    listed = client.get("/api/groups").json()
    names = {m["display_name"] for g in listed for m in g["members"]}
    assert {"Ana", "Bo", "Cy"} <= names
