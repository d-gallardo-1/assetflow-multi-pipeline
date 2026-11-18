"""Pipelines, stage movement and the KPIs that follow from it."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.engine import CommandRejected
from app.models import AuditAction, Pipeline
from app.pipelines import SPECS, stage_code

from .conftest import START, view


def test_four_pipelines_of_four_ordered_stages():
    assert [spec.pipeline.value for spec in SPECS.values()] == [
        "LAND_ACQUISITION", "BUILD_TO_SUIT", "MULTI_TENANT_PARKS", "ADVISORY_VALUATION",
    ]
    assert [stage.name for stage in SPECS[Pipeline.BUILD_TO_SUIT].stages] == [
        "Engineering Design", "Planning & Grid Permits", "Civil Execution", "Operational Handover",
    ]
    assert all(len(spec.stages) == 4 for spec in SPECS.values())


def test_seed_holds_sixteen_assets_with_two_in_the_trash(engine):
    snapshot = engine.snapshot()

    assert [len(board.assets) for board in snapshot.pipelines] == [4, 4, 3, 3]
    assert [asset.asset_id for asset in snapshot.trash] == ["AST-412", "AST-414"]
    assert snapshot.organisation.startswith("Meridian Capital Assets & Infrastructure Sites")


@pytest.mark.parametrize("spelling", ["CIVIL_EXECUTION", "civil execution", "03. Civil Execution"])
def test_stage_is_accepted_as_code_name_or_numbered_label(engine, spelling):
    engine.move("AST-405", spelling)

    moved = view(engine, "AST-405")
    assert (moved.stage, moved.stage_index, moved.stage_label) == ("CIVIL_EXECUTION", 2, "03. Civil Execution")
    assert stage_code("02. Planning & Grid Permits") == "PLANNING_GRID_PERMITS"


def test_move_writes_an_audit_entry_with_a_utc_timestamp(engine, clock):
    clock.advance(hours=3)
    engine.move("AST-401", "TECHNICAL_DUE_DILIGENCE")

    created, moved = view(engine, "AST-401").audit
    assert created.action is AuditAction.CREATED
    assert (moved.action, moved.detail) == (
        AuditAction.MOVED, "01. Site Scouting to 02. Technical Due Diligence",
    )
    assert moved.at == START.replace(hour=11)
    assert moved.at.utcoffset().total_seconds() == 0


def test_document_checklist_follows_the_stage(engine):
    before = [item.received for item in view(engine, "AST-401").document_checklist]
    engine.move("AST-401", "COMMERCIAL_NEGOTIATION")
    after = view(engine, "AST-401").document_checklist

    assert before == [True, False, False, False]
    assert [item.received for item in after] == [True, True, True, False]
    assert after[2].document == "Heads of terms"


@pytest.mark.parametrize(
    ("asset_id", "stage", "status", "fragment"),
    [
        ("AST-401", "CIVIL_EXECUTION", 422, "is not a stage of LAND_ACQUISITION"),  # another pipeline
        ("AST-401", "NOT_A_STAGE", 422, "Expected one of: SITE_SCOUTING"),
        ("AST-401", "SITE_SCOUTING", 409, "already at 01. Site Scouting"),
        ("AST-999", "TITLE_CLOSED", 404, "AST-999 does not exist"),
        ("AST-412", "UNIT_AVAILABLE", 409, "is in the trash bin"),
    ],
)
def test_rejected_moves_change_nothing(engine, asset_id, stage, status, fragment):
    before = engine.snapshot()

    with pytest.raises(CommandRejected) as rejected:
        engine.move(asset_id, stage)

    assert rejected.value.status_code == status
    assert fragment in rejected.value.detail
    after = engine.snapshot()
    assert (after.pipelines, after.trash, after.kpis, after.sequence) == (
        before.pipelines, before.trash, before.kpis, before.sequence,
    )


def test_kpis_count_active_assets_only(engine):
    kpis = engine.snapshot().kpis

    assert (kpis.active_assets, kpis.trash_assets) == (14, 2)
    # 16 seed assets total 417,987,000; AST-412 (8.9M) and AST-414 (240k) are in the trash.
    assert kpis.total_capital_value_gbp == Decimal("408847000.00")
    assert kpis.total_area_sqm == 851_900
    assert kpis.permits_verified == 9
    assert {t.pipeline.value: t.asset_count for t in kpis.capital_by_pipeline} == {
        "LAND_ACQUISITION": 4, "BUILD_TO_SUIT": 4, "MULTI_TENANT_PARKS": 3, "ADVISORY_VALUATION": 3,
    }
    assert {r.risk_level.value: r.asset_count for r in kpis.risk_distribution} == {"LOW": 5, "MEDIUM": 5, "HIGH": 4}
    assert sum(r.capital_value_gbp for r in kpis.risk_distribution) == kpis.total_capital_value_gbp


def test_funnel_is_recalculated_when_an_asset_moves(engine):
    before = engine.snapshot().kpis.funnel
    engine.move("AST-405", "OPERATIONAL_HANDOVER")  # stage 1 -> stage 4, 62.5M
    after = engine.snapshot().kpis.funnel

    assert [step.asset_count for step in before] == [4, 3, 4, 3]
    assert [step.asset_count for step in after] == [3, 3, 4, 4]
    assert before[0].capital_value_gbp - after[0].capital_value_gbp == Decimal("62500000.00")
    assert after[3].by_pipeline["BUILD_TO_SUIT"] == 2
    assert sum(step.capital_value_gbp for step in after) == engine.snapshot().kpis.total_capital_value_gbp


def test_money_is_exact_decimal_and_travels_as_a_string(engine, client):
    engine.move("AST-409", "TECHNICAL_FIT_OUT")
    state = client.get("/api/v1/state").json()

    assert state["kpis"]["total_capital_value_gbp"] == "408847000.00"
    assert state["pipelines"][0]["assets"][0]["capital_value_gbp"] == "14250000.00"
