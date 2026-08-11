"""The seam contract: the schema drives meta, chart candidates and export columns (§10).

These tests pin priority #1 — everything downstream follows from ``exercise/schema.py``.
"""
from __future__ import annotations

from app.exercise_bridge import field_names


def test_meta_exposes_full_schema(client):
    meta = client.get("/api/meta").json()
    props = set(meta["schema"]["properties"].keys())
    assert props == set(field_names())
    assert meta["field_order"] == field_names()


def test_numeric_fields_are_chart_candidates(client):
    numeric = set(client.get("/api/meta").json()["numeric_fields"])
    # numeric measurement fields are offered as chart candidates ...
    assert {"temperature_c", "absorbance_au", "dilution_factor", "replicate"} <= numeric
    # ... categorical / text / date fields are not.
    assert numeric.isdisjoint({"buffer", "sample_id", "notes", "measured_on"})


def test_export_columns_follow_schema(client):
    header = client.get("/api/export?format=csv").text.splitlines()[0].split(",")
    n = len(field_names())
    assert header[:n] == field_names()
    assert header[n:] == ["cohort", "group", "submitted_at", "superseded"]
