"""LOAD-BEARING (§B10): 60 simultaneous sessions submitting results.

No errors, and no cross-session state leakage — each session's result must land against ITS
OWN student/group, never another's. The failure mode this guards is a ruined first lesson
with two classes in the lab at once, so it is tested rather than assumed.
"""
from __future__ import annotations

import string
from concurrent.futures import ThreadPoolExecutor

from core import identity, results as R
from core.config import settings
from core.db import SessionLocal
from tests.conftest import reset_db, valid_measurement

N_SESSIONS = 60


def _kuid(i: int) -> str:
    letters = string.ascii_lowercase
    return f"{letters[i // 26 % 26]}{letters[i % 26]}z{i % 1000:03d}"


def test_60_concurrent_sessions_submit_without_error_or_leakage():
    reset_db()
    # Pre-register 60 students across 7 holds / 20 groups (a realistic class shape).
    students = []
    with SessionLocal() as s:
        cohort = identity.get_open_cohort(s)
        groups = [identity.create_group(s, cohort, hold=(i % 7) + 1, name=f"Group {i:02d}")
                  for i in range(20)]
        for i in range(N_SESSIONS):
            m = identity.register(s, _kuid(i), f"Student {i}", (i % 7) + 1,
                                  group_id=groups[i % len(groups)].id)
            students.append((m.id, m.kuid, m.group_id))

    errors: list[str] = []

    def submit(idx: int):
        """Each thread = one Streamlit session with its own DB session (no shared state)."""
        member_id, kuid, group_id = students[idx]
        try:
            with SessionLocal() as session:
                res = R.submit_result(session, member_id, valid_measurement(
                    compound_name=f"compound-{idx}", measured_logp=1.0 + idx * 0.01,
                    replicate=(idx % 10) + 1))
                return (res.id, member_id, kuid, group_id, f"compound-{idx}")
        except Exception as exc:  # noqa: BLE001 - collected and asserted below
            errors.append(f"session {idx}: {type(exc).__name__}: {exc}")
            return None

    with ThreadPoolExecutor(max_workers=N_SESSIONS) as pool:
        outcomes = list(pool.map(submit, range(N_SESSIONS)))

    assert not errors, f"{len(errors)} session(s) errored: {errors[:5]}"
    assert all(o is not None for o in outcomes), "every session must get a result"
    assert len({o[0] for o in outcomes}) == N_SESSIONS, "each write got its own row"

    # --- no cross-session state leakage: every row belongs to its own submitter ---
    with SessionLocal() as s:
        rows = R.query_results(s, latest=True)
    assert len(rows) == N_SESSIONS, f"expected {N_SESSIONS} results, got {len(rows)}"

    by_compound = {r["values"]["compound_name"]: r for r in rows}
    for _res_id, member_id, kuid, group_id, compound in outcomes:
        row = by_compound[compound]
        assert row["member_id"] == member_id, f"{compound} attributed to the wrong student"
        assert row["kuid"] == kuid, f"{compound} carries the wrong KUID (state leaked)"
        assert row["group_id"] == group_id, f"{compound} attributed to the wrong group"


def test_csv_mirror_consistent_after_concurrent_writes():
    """The mirror is rewritten on every submission; after the storm it must be complete
    and well-formed (atomic writes mean no torn file)."""
    import csv as csv_mod
    import io

    with SessionLocal() as s:
        rows = R.query_results(s, latest=False)
    text = settings.csv_path.read_text(encoding="utf-8")
    parsed = list(csv_mod.DictReader(io.StringIO(text)))
    assert parsed, "CSV mirror should not be empty"
    assert list(parsed[0].keys()) == R.columns()
    assert len(parsed) == len(rows), "mirror row count should match the database"


def test_concurrent_registration_is_safe():
    """Many students registering at once: unique group names hold, no lost registrations."""
    reset_db()
    results: list[str] = []

    def register(i: int):
        with SessionLocal() as session:
            try:
                identity.register(session, _kuid(i), f"S{i}", 1, new_group_name="Shared Group")
                results.append("ok")
            except Exception:
                # Losing the create race is fine — join instead (what the UI does on rerun).
                try:
                    cohort = identity.get_open_cohort(session)
                    groups = identity.list_groups(session, cohort, hold=1)
                    identity.register(session, _kuid(i), f"S{i}", 1, group_id=groups[0].id)
                    results.append("joined")
                except Exception as exc:  # noqa: BLE001
                    results.append(f"error: {exc}")

    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(register, range(20)))

    assert not [r for r in results if r.startswith("error")], results[:5]
    with SessionLocal() as s:
        cohort = identity.get_open_cohort(s)
        groups = identity.list_groups(s, cohort, hold=1)
    assert len([g for g in groups if g.name == "Shared Group"]) == 1, "duplicate group created"
