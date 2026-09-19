"""The API: booking decisions and reviewed changes to the facts behind them."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from dock import api, db
from dock.importer import import_workbook
from tests.fixtures.make_fixture import build


@pytest.fixture(params=["sqlite"] + (["postgres"] if os.environ.get("TEST_DATABASE_URL") else []))
def client(tmp_path, monkeypatch, request):
    db_path = os.environ["TEST_DATABASE_URL"] if request.param == "postgres" else tmp_path / "test.db"
    result = import_workbook(build(tmp_path / "tiny.xlsx"))
    conn = db.connect(db_path)
    db.initialize(conn)
    db.load_import(conn, result, {"totals": result.stats["totals"]})
    conn.close()
    monkeypatch.setattr(api, "DB_PATH", db_path)
    with TestClient(api.app) as c:
        yield c


def berth_id(client, name):
    return next(b["id"] for b in client.get("/api/berths").json() if b["name"] == name)


def vessel_id(client, name):
    return client.get("/api/vessels", params={"q": name}).json()[0]["id"]


def test_berths_and_vessels_are_served(client):
    names = [b["name"] for b in client.get("/api/berths").json()]
    assert names[:3] == ["North Pier West", "North Pier Face", "North Pier East"]
    [compass] = client.get("/api/vessels", params={"q": "golden compass"}).json()
    assert compass["length_ft"] == 120


def test_a_vessel_that_does_not_fit_is_refused_with_the_numbers(client):
    body = {"berth_id": berth_id(client, "North Pier Face"), "vessel_id": vessel_id(client, "golden compass"),
            "start": "2026-07-01", "end": "2026-07-02"}
    judged = client.post("/api/check", json=body).json()
    assert judged["verdict"] == "conflict" and judged["findings"][0]["code"] == "fit"
    assert judged["findings"][0]["numbers"]["over_ft"] == 45
    refused = client.post("/api/reservations", json=body)
    assert refused.status_code == 409 and refused.json()["detail"]["verdict"] == "conflict"
    assert client.get("/api/reservations", params={"start": "2026-07-01", "end": "2026-07-02"}).json() == []


def test_an_override_reason_saves_a_refused_booking_and_keeps_the_reason(client):
    body = {"berth_id": berth_id(client, "North Pier Face"), "vessel_id": vessel_id(client, "golden compass"),
            "start": "2026-07-01", "end": "2026-07-02", "override_reason": "rafting alongside, dockmaster approved"}
    saved = client.post("/api/reservations", json=body)
    assert saved.status_code == 201
    assert saved.json()["reservation"]["override_reason"].startswith("rafting")
    assert saved.json()["check"]["verdict"] == "conflict"


def test_unknown_length_blocks_until_the_length_is_entered(client):
    unknown = client.post("/api/vessels", json={"name": "M/V Newcomer", "type_prefix": "M/V"}).json()
    body = {"berth_id": berth_id(client, "North Pier West"), "vessel_id": unknown["id"],
            "start": "2026-08-01", "end": "2026-08-03"}
    assert client.post("/api/reservations", json=body).status_code == 409
    assert client.post("/api/check", json=body).json()["verdict"] == "unknown"
    client.patch(f"/api/vessels/{unknown['id']}", json={"length_ft": 80})
    assert client.post("/api/reservations", json=body).status_code == 201


def test_a_second_boat_on_a_shared_face_is_fine_until_the_face_is_full(client):
    west = berth_id(client, "North Pier West")
    big = client.post("/api/vessels", json={"name": "R/V Atlantis", "length_ft": 274}).json()
    mid = client.post("/api/vessels", json={"name": "Barge Wide", "length_ft": 100}).json()
    small = client.post("/api/vessels", json={"name": "R/V Tioga", "length_ft": 60}).json()
    for v in (big, mid):
        assert client.post("/api/reservations", json={"berth_id": west, "vessel_id": v["id"],
                                                      "start": "2026-09-01", "end": "2026-09-10"}).status_code == 201
    refused = client.post("/api/reservations", json={"berth_id": west, "vessel_id": small["id"],
                                                     "start": "2026-09-05", "end": "2026-09-06"})
    assert refused.status_code == 409
    [cap] = [f for f in refused.json()["detail"]["findings"] if f["code"] == "capacity"]
    assert cap["numbers"]["used_ft"] == 464 and "R/V Atlantis" in cap["message"]


def test_suggestions_offer_the_smallest_fitting_berth_first(client):
    vid = vessel_id(client, "golden compass")  # 120'
    out = client.get("/api/suggest", params={"vessel_id": vid, "start": "2026-07-01", "end": "2026-07-03"}).json()
    assert [s["berth"]["name"] for s in out][:2] == ["North Pier East", "North Pier West"]


def test_cancelling_never_needs_a_check_and_frees_the_berth(client):
    face = berth_id(client, "North Pier Face")
    tiny = client.post("/api/vessels", json={"name": "F/V Tiny", "length_ft": 20}).json()
    first = client.post("/api/reservations", json={"berth_id": face, "vessel_id": tiny["id"],
                                                   "start": "2026-10-01", "end": "2026-10-02"}).json()["reservation"]
    ev = {"berth_id": face, "kind": "event", "title": "Community sail day", "start": "2026-10-01", "end": "2026-10-01"}
    assert client.post("/api/reservations", json=ev).status_code == 409
    patched = client.patch(f"/api/reservations/{first['id']}", json={"status": "cancelled"})
    assert patched.status_code == 200 and patched.json()["reservation"]["status"] == "cancelled"
    assert client.post("/api/reservations", json=ev).status_code == 201


def test_loads_describe_each_day_for_drawing(client):
    west = berth_id(client, "North Pier West")
    rows = client.get("/api/loads", params={"berth_id": west, "start": "1998-08-01", "end": "1998-08-05"}).json()
    assert [len(r["occupants"]) for r in rows] == [0, 1, 1, 1, 0]  # F/V Swift Dory, Aug 2-4
    assert rows[1]["known_ft"] == 42 and rows[1]["over_capacity"] is False


def test_issues_and_audit_are_exposed(client):
    issues = client.get("/api/issues", params={"kind": "mislabelled_month"}).json()
    assert issues["counts"]["mislabelled_month"] == 1 and issues["issues"][0]["sheet"] == "2010"
    assert "totals" in client.get("/api/audit").json()


def test_bad_input_is_a_422_not_a_crash(client):
    body = {"berth_id": berth_id(client, "North Pier Face"), "vessel_id": vessel_id(client, "golden compass"),
            "start": "2026-07-05", "end": "2026-07-01"}
    assert client.post("/api/check", json=body).status_code == 422
    assert client.post("/api/vessels", json={"name": "Bad", "length_ft": -5}).status_code == 422
    assert client.post("/api/reservations", json={**body, "berth_id": 999, "end": "2026-07-06"}).status_code == 404


def test_a_stored_override_does_not_exempt_a_later_edit(client):
    west, face = berth_id(client, "North Pier West"), berth_id(client, "North Pier Face")
    vid = vessel_id(client, "golden compass")  # 120'
    saved = client.post("/api/reservations", json={"berth_id": west, "vessel_id": vid, "start": "2026-11-01",
                                                   "end": "2026-11-02", "override_reason": "decoration"}).json()["reservation"]
    moved = client.patch(f"/api/reservations/{saved['id']}", json={"berth_id": face})
    assert moved.status_code == 409  # the old reason was about another berth
    assert client.patch(f"/api/reservations/{saved['id']}", json={"berth_id": face, "override_reason": "rafting"}).status_code == 200


def test_reversed_loads_and_colliding_renames_are_4xx(client):
    assert client.get("/api/loads", params={"start": "2026-01-10", "end": "2026-01-01"}).status_code == 422
    a = client.post("/api/vessels", json={"name": "M/V Alpha One", "length_ft": 50}).json()
    b = client.post("/api/vessels", json={"name": "M/V Beta Two", "length_ft": 50}).json()
    assert client.patch(f"/api/vessels/{b['id']}", json={"name": "m/v ALPHA ONE"}).status_code == 409
    assert client.patch(f"/api/vessels/{a['id']}", json={"name": "M/V Alpha One"}).status_code == 200


def test_a_length_can_be_cleared_back_to_unknown(client):
    v = client.post("/api/vessels", json={"name": "F/V Measured", "length_ft": 40}).json()
    cleared = client.patch(f"/api/vessels/{v['id']}", json={"length_ft": None}).json()
    assert cleared["length_ft"] is None


def test_a_post_with_an_id_cannot_slip_past_the_referee(client):
    face = berth_id(client, "North Pier Face")
    tiny = client.post("/api/vessels", json={"name": "F/V Probe", "length_ft": 20}).json()
    first = client.post("/api/reservations", json={"berth_id": face, "vessel_id": tiny["id"],
                                                   "start": "2026-10-10", "end": "2026-10-11"}).json()["reservation"]
    ev = {"berth_id": face, "kind": "event", "title": "Donor reception", "start": "2026-10-10", "end": "2026-10-10", "id": first["id"]}
    assert client.post("/api/reservations", json=ev).status_code == 422


def test_unknown_fields_and_empty_edits_are_refused(client):
    face = berth_id(client, "North Pier Face")
    vid = vessel_id(client, "golden compass")
    body = {"berth_id": face, "vessel_id": vid, "start": "2026-07-01", "end": "2026-07-02", "bogus": 1}
    assert client.post("/api/check", json=body).status_code == 422
    assert client.patch(f"/api/vessels/{vid}", json={}).status_code == 422
    assert client.patch(f"/api/vessels/{vid}", json={"lenght_ft": 55}).status_code == 422
    ev = {"berth_id": face, "kind": "event", "title": "Regatta", "start": "2026-07-01", "end": "2026-07-01", "vessel_id": vid}
    assert client.post("/api/check", json=ev).status_code == 422


def test_a_note_can_be_added_to_a_stay_the_referee_cannot_judge(client):
    imported = client.get("/api/reservations", params={"start": "2009-01-01", "end": "2009-01-31"}).json()
    unknown = next(r for r in imported if r["vessel"] and r["vessel"]["length_ft"] is None)  # M/V Northern Harbor
    out = client.patch(f"/api/reservations/{unknown['id']}", json={"notes": "checked by phone"})
    assert out.status_code == 200 and out.json()["check"] is None
    assert out.json()["reservation"]["notes"] == "checked by phone"


def test_a_booking_survives_a_second_application_start(client):
    face = berth_id(client, "North Pier Face")
    saved = client.post("/api/reservations", json={"berth_id": face, "kind": "event",
                        "title": "Persistence check", "start": "2026-12-01", "end": "2026-12-01"})
    assert saved.status_code == 201
    reservation_id = saved.json()["reservation"]["id"]
    api.ensure_data()
    assert client.get(f"/api/reservations/{reservation_id}").json()["title"] == "Persistence check"


def test_simultaneous_full_berth_bookings_cannot_both_save(client):
    face = berth_id(client, "North Pier Face")
    ready = Barrier(2)

    def book(title):
        ready.wait(timeout=5)
        return client.post("/api/reservations", json={"berth_id": face, "kind": "event", "title": title,
                           "start": "2026-12-02", "end": "2026-12-02"}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(book, ["Community sail day", "Student visit"]))
    assert sorted(results) == [201, 409]


def test_simultaneous_duplicate_vessels_return_a_conflict_instead_of_a_server_error(client):
    ready = Barrier(2)

    def create(_):
        ready.wait(timeout=5)
        return client.post("/api/vessels", json={"name": "R/V Concurrency", "length_ft": 50}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, [1, 2]))
    assert sorted(results) == [201, 409]


def test_vercel_refuses_to_use_ephemeral_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "temporary.db")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        api.ensure_data()


def measured_stay(client, name="F/V Measurement", length=30, berth="North Pier Face"):
    v = client.post("/api/vessels", json={"name": name, "length_ft": length}).json()
    response = client.post("/api/reservations", json={"berth_id": berth_id(client, berth), "vessel_id": v["id"],
                           "start": "2030-01-01", "end": "2030-01-02"})
    assert response.status_code == 201, response.text
    return v, response.json()["reservation"]


@pytest.mark.parametrize("new_length,verdict", [(120, "conflict"), (None, "unknown")])
def test_measurement_preview_does_not_save_and_blocking_edits_need_a_recorded_review(client, new_length, verdict):
    v, stay = measured_stay(client)
    url = f"/api/vessels/{v['id']}"
    body = {"length_ft": new_length}
    preview = client.post(url + "/check-change", json=body).json()["impact"]
    assert preview["affected_count"] == 1 and preview["blocking_count"] == 1
    assert preview["reservations"][0]["before"]["verdict"] == "ok"
    assert preview["reservations"][0]["after"]["verdict"] == verdict
    assert client.get("/api/vessels", params={"q": v["name"]}).json()[0]["length_ft"] == 30
    for extra in ({}, {"impact_reason": "   ", "impact_token": preview["token"]}, {"impact_reason": "measured again"}):
        refused = client.patch(url, json={**body, **extra})
        assert refused.status_code == 409
        assert refused.json()["detail"]["code"] == "measurement_review"
    saved = client.patch(url, json={**body, "impact_reason": "Corrected from the vessel's current specification", "impact_token": preview["token"]})
    assert saved.status_code == 200
    assert saved.json()["length_ft"] == new_length
    [review] = client.get(url + "/changes").json()
    assert review["length_before"] == 30 and review["length_after"] == new_length
    assert review["reason"] == "Corrected from the vessel's current specification"
    assert review["impact"]["reservations"][0]["reservation"]["id"] == stay["id"]
    assert review["impact"]["reservations"][0]["after"]["verdict"] == verdict


def test_length_correction_reviews_neighbours_as_well_as_the_changed_vessels_stay(client):
    a, own = measured_stay(client, "M/V First", 200, "North Pier West")
    _, neighbour = measured_stay(client, "M/V Neighbour", 100, "North Pier West")
    impact = client.post(f"/api/vessels/{a['id']}/check-change", json={"length_ft": 305}).json()["impact"]
    assert impact["blocking_count"] == 2
    assert {i["reservation"]["id"] for i in impact["reservations"]} == {own["id"], neighbour["id"]}
    assert all(any(f["code"] == "capacity" for f in i["after"]["findings"]) for i in impact["reservations"])


def test_an_acknowledgement_cannot_be_reused_after_the_affected_booking_changes(client):
    v, stay = measured_stay(client)
    url = f"/api/vessels/{v['id']}"
    impact = client.post(url + "/check-change", json={"length_ft": 120}).json()["impact"]
    client.patch(f"/api/reservations/{stay['id']}", json={"end": "2030-01-03"})
    stale = client.patch(url, json={"length_ft": 120, "impact_reason": "Reviewed", "impact_token": impact["token"]})
    assert stale.status_code == 409
    assert stale.json()["detail"]["impact"]["token"] != impact["token"]
    assert client.get("/api/vessels", params={"q": v["name"]}).json()[0]["length_ft"] == 30
    assert client.get(url + "/changes").json() == []


def test_cancelled_stays_do_not_block_measurement_corrections(client):
    v, stay = measured_stay(client)
    client.patch(f"/api/reservations/{stay['id']}", json={"status": "cancelled"})
    out = client.patch(f"/api/vessels/{v['id']}", json={"length_ft": 120})
    assert out.status_code == 200 and out.json()["impact"]["affected_count"] == 0


def test_failure_to_record_a_measurement_review_rolls_back_the_measurement(client, monkeypatch):
    v = client.post("/api/vessels", json={"name": "F/V Atomic change", "length_ft": 30}).json()
    def fail(*_):
        raise RuntimeError("review storage unavailable")
    monkeypatch.setattr(db, "record_vessel_change", fail)
    with pytest.raises(RuntimeError, match="review storage unavailable"):
        client.patch(f"/api/vessels/{v['id']}", json={"length_ft": 40})
    assert client.get("/api/vessels", params={"q": v["name"]}).json()[0]["length_ft"] == 30
    assert client.get(f"/api/vessels/{v['id']}/changes").json() == []


@pytest.mark.parametrize("field", ["name", "notes", "rafts_ok"])
def test_required_vessel_fields_cannot_be_cleared_to_null(client, field):
    vid = vessel_id(client, "golden compass")
    assert client.patch(f"/api/vessels/{vid}", json={field: None}).status_code == 422


def test_the_measurement_table_upgrade_keeps_existing_bookings(client):
    _, stay = measured_stay(client)
    conn = db.connect(api.DB_PATH)
    db.begin_write(conn)
    conn.execute("DROP TABLE vessel_changes")  # disposable fixture: simulate the prior schema
    conn.commit()
    conn.close()
    api.ensure_data()
    saved = client.get(f"/api/reservations/{stay['id']}").json()
    assert saved["vessel"]["name"] == "F/V Measurement"
    assert client.get(f"/api/vessels/{saved['vessel']['id']}/changes").json() == []
