"""SQLite WAL concurrency: tens of simultaneous writers must all land (§5.4, §15.2)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from app.db import SessionLocal
from app import services
from tests.conftest import _reset_db, valid_measurement

N_WRITERS = 30


def test_many_concurrent_writers_all_persist():
    _reset_db()
    # One shared group; every writer appends a result to it concurrently.
    with SessionLocal() as s:
        group = services.create_group(s, "Concurrent", ["Ana"])
        group_id = group.id

    def submit(i: int) -> int:
        with SessionLocal() as session:
            r = services.submit_result(session, group_id, valid_measurement(replicate=(i % 10) + 1))
            return r.id

    with ThreadPoolExecutor(max_workers=N_WRITERS) as pool:
        ids = list(pool.map(submit, range(N_WRITERS)))

    assert len(set(ids)) == N_WRITERS  # every write got its own row, none lost
    with SessionLocal() as s:
        rows = services.query_results(s, cohort="all", latest=True)
    assert len(rows) == N_WRITERS


def test_concurrent_group_creation_unique_names():
    """Two writers racing to create the same group name: one wins, one gets a clean 409."""
    _reset_db()
    outcomes = []

    def make():
        with SessionLocal() as session:
            try:
                services.create_group(session, "SameName", [])
                outcomes.append("ok")
            except services.ConflictError:
                outcomes.append("conflict")

    with ThreadPoolExecutor(max_workers=2) as pool:
        for _ in range(2):
            pool.submit(make)

    # At least one succeeds; the DB never ends up with two 'SameName' groups.
    with SessionLocal() as s:
        groups = services.list_groups(s, services.get_open_cohort(s))
    assert len([g for g in groups if g["name"] == "SameName"]) == 1
