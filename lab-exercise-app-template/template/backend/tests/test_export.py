"""Export: column stability across cohorts + public/admin gating (§9, §15.3, §15.10)."""
from __future__ import annotations

import io

from app.exercise_bridge import field_names
from tests.conftest import DEFAULT_COHORT, SECOND_COHORT, valid_measurement

EXPECTED_COLUMNS = field_names() + ["cohort", "group", "submitted_at", "superseded"]


def _seed_result(client, group_name="G", **vals):
    g = client.post("/api/groups", json={"name": group_name, "members": []}).json()
    return client.post(f"/api/groups/{g['id']}/results", json=valid_measurement(**vals)).json()


def test_public_latest_csv_has_schema_columns(client):
    _seed_result(client, absorbance_au=0.3)
    resp = client.get("/api/export?format=csv&cohort=all&history=false")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    header = resp.text.splitlines()[0]
    assert header == ",".join(EXPECTED_COLUMNS)


def test_full_history_and_parquet_are_admin_only(client):
    assert client.get("/api/export?format=csv&history=true").status_code == 401
    assert client.get("/api/export?format=parquet&history=false").status_code == 401


def test_admin_full_history_shows_superseded_rows(admin_client):
    first = _seed_result(admin_client, absorbance_au=0.3)
    admin_client.post(f"/api/results/{first['id']}/supersede", json=valid_measurement(absorbance_au=0.9))
    resp = admin_client.get("/api/export?format=csv&cohort=all&history=true")
    assert resp.status_code == 200
    lines = resp.text.strip().splitlines()
    assert len(lines) == 3  # header + 2 rows
    # exactly one row is flagged superseded
    superseded_idx = EXPECTED_COLUMNS.index("superseded")
    flags = [row.split(",")[superseded_idx] for row in lines[1:]]
    assert sorted(flags) == ["False", "True"]


def test_column_stability_across_cohorts(admin_client):
    _seed_result(admin_client, "Team1", absorbance_au=0.2)
    admin_client.post("/api/admin/cohorts/close")
    admin_client.post("/api/admin/cohorts", json={"label": SECOND_COHORT})
    _seed_result(admin_client, "Team2", absorbance_au=0.8)

    resp = admin_client.get("/api/export?format=parquet&cohort=all&history=false")
    assert resp.status_code == 200
    import pandas as pd

    frame = pd.read_parquet(io.BytesIO(resp.content))
    # Same columns, same order, regardless of which cohort a row came from.
    assert list(frame.columns) == EXPECTED_COLUMNS
    assert set(frame["cohort"]) == {DEFAULT_COHORT, SECOND_COHORT}


def test_export_empty_still_has_header(client):
    resp = client.get("/api/export?format=csv&cohort=all&history=false")
    assert resp.status_code == 200
    assert resp.text.splitlines()[0] == ",".join(EXPECTED_COLUMNS)


def test_export_persists_artifact_to_volume(client):
    from app.config import settings

    _seed_result(client, absorbance_au=0.4)
    client.get("/api/export?format=csv&cohort=all&history=false")
    # An artifact was written to the exports dir on the volume (atomically).
    files = list(settings.exports_dir.glob("*.csv"))
    assert files, "export should persist a copy to DATA_DIR/exports"
    # No leftover temp files from the atomic write.
    assert not list(settings.exports_dir.glob(".*.tmp-*"))


def test_admin_exports_listing_filters_platform_artifacts(admin_client):
    from app.config import settings

    _seed_result(admin_client, absorbance_au=0.4)
    admin_client.get("/api/export?format=csv&cohort=all&history=false")
    # Simulate the platform artifacts that live in every mounted volume.
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    (settings.exports_dir / ".AVI_SUCCESS").write_text("")
    (settings.exports_dir / "lost+found").mkdir(exist_ok=True)
    names = {e["name"] for e in admin_client.get("/api/admin/exports").json()}
    assert ".AVI_SUCCESS" not in names and "lost+found" not in names
    assert any(n.endswith(".csv") for n in names)
