"""The storage adapters: the same guarantees on SQLite and on PostgreSQL.

PostgreSQL cases run only when TEST_DATABASE_URL points at disposable test
storage (CI provides one); its contents are replaced by these tests.
"""
import os
import threading
from datetime import date

import pytest

from dock import api, db
from dock.importer import ImportResult, import_workbook
from dock.models import DayRange, Reservation, ReservationKind, Vessel
from tests.fixtures.make_fixture import build

ENGINES = ["sqlite"] + (["postgres"] if os.environ.get("TEST_DATABASE_URL") else [])


@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    return import_workbook(build(tmp_path_factory.mktemp("wb") / "tiny.xlsx"))


@pytest.fixture(params=ENGINES)
def target(request, tmp_path):
    return os.environ["TEST_DATABASE_URL"] if request.param == "postgres" else str(tmp_path / "test.db")


@pytest.fixture()
def conn(target, tiny):
    c = db.connect(target)
    db.initialize(c)
    db.load_import(c, tiny)
    yield c
    c.close()


def test_a_manual_booking_after_an_import_gets_the_next_free_id(conn, tiny):
    vessel = db.insert_vessel(conn, Vessel("M/V Newcomer", 40.5, "M/V", rafts_ok=True))
    assert vessel.id == max(v.id for v in tiny.vessels) + 1
    assert db.vessel(conn, vessel.id) == vessel  # floats, booleans and None survive the round trip
    berth = db.berths(conn)[0]
    saved = db.insert_reservation(conn, Reservation(berth.id, ReservationKind.VESSEL, DayRange(date(2030, 1, 1), date(2030, 1, 2)), vessel=vessel))
    assert saved.id == max(r.id for r in tiny.reservations) + 1


def test_sql_without_parameters_may_contain_a_percent_sign(conn):
    rows = conn.execute("SELECT name FROM vessels WHERE name_key LIKE 'rv golden%' ORDER BY name").fetchall()
    assert [r["name"] for r in rows] == ["R/V Golden Compass"]


def test_a_failed_write_cannot_be_committed_by_mistake(conn):
    db.begin_write(conn)
    with pytest.raises(Exception, match="(?i)foreign key"):
        conn.execute("INSERT INTO annotations (berth_id, day, text, label) VALUES (?, ?, ?, ?)", (999, None, "x", "x"))
    if hasattr(conn, "raw"):  # PostgreSQL: the transaction is now failed, and commit() must say so
        with pytest.raises(RuntimeError, match="failed"):
            conn.commit()
    conn.rollback()
    assert not conn.in_transaction
    assert conn.execute("SELECT COUNT(*) AS n FROM annotations").fetchone()["n"] == 1


def test_concurrent_first_starts_seed_the_ledger_exactly_once(target, tiny, tmp_path, monkeypatch):
    if not target.startswith("postgres"):
        pytest.skip("SQLite runs one process at a time here")
    c = db.connect(target)
    db.initialize(c)
    db.load_import(c, ImportResult())
    c.close()
    monkeypatch.setattr(api, "DB_PATH", target)
    monkeypatch.setattr(api, "SAMPLE", build(tmp_path / "seed.xlsx"))
    errors = []

    def start():
        try:
            api.ensure_data()
        except Exception as e:  # noqa: BLE001 - the point is to collect every failure
            errors.append(repr(e))

    threads = [threading.Thread(target=start) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert not any(t.is_alive() for t in threads), "a cold-start worker is still blocked"
    assert errors == []
    c = db.connect(target)
    try:
        assert len(db.reservations(c)) == len(tiny.reservations)
        assert len(db.berths(c)) == len(tiny.berths)
        assert len(db.vessels(c)) == len(tiny.vessels)
    finally:
        c.close()


def test_connecting_does_not_wait_behind_an_open_write(target, tiny):
    a = db.connect(target)
    db.initialize(a)
    db.load_import(a, tiny)
    db.begin_write(a)
    try:
        opened = threading.Event()

        def connect_meanwhile():
            b = db.connect(target)
            opened.set()
            b.close()

        worker = threading.Thread(target=connect_meanwhile, daemon=True)
        worker.start()
        assert opened.wait(5), "a second connection queued behind the open write transaction"
    finally:
        a.rollback()
        a.close()
        worker.join(5)
    assert not worker.is_alive()


def test_an_unsupported_database_url_is_not_a_sqlite_filename():
    with pytest.raises(ValueError, match="postgresql"):
        db.connect("mysql://not-a-local-file")
