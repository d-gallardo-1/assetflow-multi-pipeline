"""HTTP contract: read side, asset commands, trash commands, stream."""

from __future__ import annotations

import asyncio

from app.broadcaster import QUEUE_SIZE
from app.sse import event_stream

from .conftest import API, active_ids, parse_sse, trash_ids, view

NEW_ASSET = {
    "name": "Solent Reserve Plot", "pipeline": "LAND_ACQUISITION", "region": "Solent", "area_sqm": 5000,
    "capital_value_gbp": "1250000.00", "lead_engineer": "Ada Fenwick-Lowe", "lat": 50.9, "lon": -1.4,
    "grid_capacity_mva": 2.5, "permits_verified": False, "risk_level": "MEDIUM",
}


def test_health_and_state(client):
    health = client.get(f"{API}/health").json()
    state = client.get(f"{API}/state").json()

    assert (health["status"], health["synthetic_data"]) == ("ok", True)
    assert [board["pipeline"] for board in state["pipelines"]] == [
        "LAND_ACQUISITION", "BUILD_TO_SUIT", "MULTI_TENANT_PARKS", "ADVISORY_VALUATION",
    ]
    assert [stage["label"] for stage in state["pipelines"][3]["stages"]] == [
        "01. Scope Intake", "02. Field Inspection", "03. Compliance Modelling", "04. Certified Report",
    ]
    assert (state["retention_days"], state["kpis"]["active_assets"], len(state["trash"])) == (30, 14, 2)
    first = state["pipelines"][0]["assets"][0]
    assert first["gis_coords"] == {"lat": 54.6, "lon": -1.2}
    assert (first["is_deleted"], first["deleted_at"], first["retention_days_left"]) == (False, None, None)
    assert state["trash"][0]["is_deleted"] is True
    assert state["generated_at"].endswith("Z")


def test_create_assigns_the_id_and_defaults_to_the_first_stage(client, engine):
    first = client.post(f"{API}/assets", json=NEW_ASSET)
    second = client.post(f"{API}/assets", json={**NEW_ASSET, "stage": "Title Closed"})

    assert (first.status_code, first.json()["asset_id"], second.json()["asset_id"]) == (201, "AST-417", "AST-418")
    assert view(engine, "AST-417").stage == "SITE_SCOUTING"
    assert view(engine, "AST-418").stage == "TITLE_CLOSED"
    assert engine.snapshot().kpis.active_assets == 16


def test_create_refuses_invalid_input_and_an_id_in_use(client, engine):
    cases = [
        {**NEW_ASSET, "lat": 91},
        {**NEW_ASSET, "stage": "CIVIL_EXECUTION"},
        {**NEW_ASSET, "capital_value_gbp": "1.999"},
        {**NEW_ASSET, "owner": "unknown field"},
        {key: value for key, value in NEW_ASSET.items() if key != "region"},
    ]
    assert [client.post(f"{API}/assets", json=body).status_code for body in cases] == [422] * 5
    assert client.post(f"{API}/assets", json={**NEW_ASSET, "asset_id": "AST-401"}).status_code == 409
    assert client.post(f"{API}/assets", json={**NEW_ASSET, "asset_id": "AST-412"}).status_code == 409
    assert engine.snapshot().sequence == 0


def test_stage_move_status_codes(client, engine):
    def move(asset_id: str, stage: str) -> int:
        return client.patch(f"{API}/assets/{asset_id}/stage", json={"stage": stage}).status_code

    assert move("AST-401", "TECHNICAL_DUE_DILIGENCE") == 200
    assert move("AST-401", "CIVIL_EXECUTION") == 422  # a stage of another pipeline
    assert move("AST-999", "TITLE_CLOSED") == 404  # unknown asset
    assert move("AST-412", "UNIT_AVAILABLE") == 409  # in the trash bin
    assert move("reset", "TITLE_CLOSED") == 422  # not an asset id at all
    assert view(engine, "AST-401").stage == "TECHNICAL_DUE_DILIGENCE"


def test_delete_restore_and_purge_over_http(client, engine):
    assert client.delete(f"{API}/assets/AST-403").status_code == 200
    assert client.delete(f"{API}/assets/AST-403").status_code == 409
    assert trash_ids(engine)[0] == "AST-403"

    assert client.post(f"{API}/trash/AST-403/restore").status_code == 200
    assert client.post(f"{API}/trash/AST-403/restore").status_code == 409
    assert view(engine, "AST-403").stage == "COMMERCIAL_NEGOTIATION"

    assert client.delete(f"{API}/trash/AST-403/purge").status_code == 409  # active
    assert client.delete(f"{API}/trash/AST-414/purge").status_code == 200
    assert client.delete(f"{API}/trash/AST-414/purge").status_code == 404
    assert trash_ids(engine) == ["AST-412"]


def test_reset_restores_the_seed_and_static_routes_are_not_read_as_ids(client, engine):
    client.delete(f"{API}/assets/AST-401")
    client.post(f"{API}/assets", json=NEW_ASSET)

    assert client.post(f"{API}/assets/reset").status_code == 200
    assert len(active_ids(engine)) == 14
    assert trash_ids(engine) == ["AST-412", "AST-414"]
    assert client.get(f"{API}/assets/sample-csv").status_code == 200
    assert client.get(f"{API}/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 404


def test_stream_sends_a_full_snapshot_then_an_update_after_a_change(engine):
    async def scenario():
        first = event_stream(engine, heartbeat_seconds=0.05)
        second = event_stream(engine, heartbeat_seconds=0.05)
        opening = []
        for stream in (first, second):
            assert await anext(stream) == "retry: 3000\n\n"
            opening.append(parse_sse(await anext(stream)))
        engine.soft_delete("AST-401")
        updates = [parse_sse(await anext(stream)) for stream in (first, second)]
        heartbeat = await anext(first)
        await first.aclose()
        await second.aclose()
        return opening, updates, heartbeat

    opening, updates, heartbeat = asyncio.run(scenario())

    assert [event for event, _ in opening] == ["snapshot", "snapshot"]
    assert opening[0][1]["kpis"]["active_assets"] == 14
    for event, data in updates:  # every connected client gets the same full state
        assert event == "update"
        assert sum(len(board["assets"]) for board in data["pipelines"]) == 13
        assert data["trash"][0]["asset_id"] == "AST-401"
    assert heartbeat == "event: heartbeat\ndata: {}\n\n"
    assert engine.subscriber_count == 0


def test_stream_endpoint_headers_and_max_events(client):
    with client.stream("GET", f"{API}/stream", params={"max_events": 1}) as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["x-accel-buffering"] == "no"
        frames = [frame for frame in "".join(response.iter_text()).split("\n\n") if frame.strip()]

    assert frames[0] == "retry: 3000"
    assert parse_sse(frames[1])[0] == "snapshot"


def test_every_command_publishes_exactly_one_snapshot_and_refusals_none(client, engine):
    queue = engine.subscribe()
    sample = client.get(f"{API}/assets/sample-csv").content
    commands = [
        lambda: client.patch(f"{API}/assets/AST-401/stage", json={"stage": "TITLE_CLOSED"}),
        lambda: client.delete(f"{API}/assets/AST-401"),
        lambda: client.post(f"{API}/trash/AST-401/restore"),
        lambda: client.delete(f"{API}/trash/AST-412/purge"),
        lambda: client.post(f"{API}/assets", json=NEW_ASSET),
        lambda: client.post(f"{API}/assets/import-csv", content=sample),
        lambda: client.post(f"{API}/assets/reset"),
    ]
    for expected, command in enumerate(commands, start=1):
        command()
        assert queue.qsize() == 1
        assert queue.get_nowait().sequence == expected

    client.patch(f"{API}/assets/AST-401/stage", json={"stage": "CIVIL_EXECUTION"})
    client.delete(f"{API}/trash/AST-401/purge")
    client.post(f"{API}/assets/import-csv", content=b"not,a,register\n1,2,3")
    assert queue.empty()


def test_slow_subscriber_queue_is_bounded_and_keeps_the_latest_snapshot(engine):
    queue = engine.subscribe()
    for _ in range(50):
        engine.publish()

    assert queue.qsize() == QUEUE_SIZE
    last = None
    while not queue.empty():
        last = queue.get_nowait()
    assert last.sequence == 50
