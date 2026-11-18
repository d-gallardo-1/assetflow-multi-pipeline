"""Input hardening found in review: control characters, id range, chunked uploads."""

from __future__ import annotations

from .conftest import API
from .test_api import NEW_ASSET


def test_text_with_control_characters_is_refused_so_the_export_cannot_break(client, engine):
    created = client.post(f"{API}/assets", json={**NEW_ASSET, "name": "Solent\x01Plot"})
    row = "AST-601,Humber\x0cPlot,LAND_ACQUISITION,SITE_SCOUTING,Humber,1200,250000.50,Ada Fenwick-Lowe,53.7,-0.3,4,yes,LOW"
    header = "asset_id,name,pipeline,stage,region,area_sqm,capital_value_gbp,lead_engineer,lat,lon,grid_capacity_mva,permits_verified,risk_level"
    report = client.post(f"{API}/assets/import-csv", content=f"{header}\n{row}".encode()).json()

    assert created.status_code == 422
    assert (report["imported"], report["errors"][0]["column"]) == ([], "name")
    assert "control characters" in report["errors"][0]["reason"]
    assert client.get(f"{API}/assets/export-xlsx").status_code == 200


def test_assigned_ids_stay_inside_the_id_pattern(client, engine):
    client.post(f"{API}/assets", json={**NEW_ASSET, "asset_id": "AST-999999"})

    assigned = client.post(f"{API}/assets", json=NEW_ASSET).json()["asset_id"]

    assert assigned == "AST-417"  # the first free number, not AST-1000000
    assert client.delete(f"{API}/assets/{assigned}").status_code == 200


def test_upload_limit_holds_for_a_body_without_a_declared_length(client, engine):
    def chunks():
        for _ in range(40):
            yield b"x" * 10_000  # 400 KB in total, sent chunked

    response = client.post(f"{API}/assets/import-csv", content=chunks())

    assert "content-length" not in response.request.headers
    assert (response.status_code, response.json()["detail"]) == (413, "The file is larger than the 256 KB limit.")
    assert engine.snapshot().sequence == 0
