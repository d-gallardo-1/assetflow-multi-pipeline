"""Soft-delete lifecycle: active, trash, restore, purge and clock-driven retention."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.engine import CommandRejected
from app.main import build_engine
from app.models import AuditAction

from .conftest import START, active_ids, trash_ids, view


def test_soft_delete_moves_the_asset_from_the_board_to_the_trash(engine):
    engine.soft_delete("AST-407")

    assert "AST-407" not in active_ids(engine)
    assert trash_ids(engine)[0] == "AST-407"  # most recent deletion first
    deleted = view(engine, "AST-407")
    assert (deleted.deleted_at, deleted.is_deleted, deleted.retention_days_left) == (START, True, 30)
    assert deleted.purge_at == START + timedelta(days=30)


def test_deleted_asset_leaves_the_kpis(engine):
    before = engine.snapshot().kpis
    engine.soft_delete("AST-407")  # 134M, 52,000 sqm, HIGH risk
    after = engine.snapshot().kpis

    assert (after.active_assets, after.trash_assets) == (13, 3)
    assert before.total_capital_value_gbp - after.total_capital_value_gbp == 134_000_000
    assert before.total_area_sqm - after.total_area_sqm == 52_000


def test_restore_returns_the_asset_to_its_exact_pipeline_and_stage(engine):
    engine.move("AST-407", "OPERATIONAL_HANDOVER")
    engine.soft_delete("AST-407")
    engine.restore("AST-407")

    restored = view(engine, "AST-407")
    assert (restored.pipeline.value, restored.stage) == ("BUILD_TO_SUIT", "OPERATIONAL_HANDOVER")
    assert (restored.deleted_at, restored.is_deleted, restored.retention_days_left) == (None, False, None)
    assert "AST-407" in active_ids(engine)
    assert engine.snapshot().kpis.active_assets == 14


def test_audit_trail_survives_delete_and_restore(engine, clock):
    engine.move("AST-407", "OPERATIONAL_HANDOVER")
    clock.advance(days=2)
    engine.soft_delete("AST-407")
    in_trash = [entry.action for entry in view(engine, "AST-407").audit]
    clock.advance(days=1)
    engine.restore("AST-407")

    audit = view(engine, "AST-407").audit
    assert in_trash == [AuditAction.CREATED, AuditAction.MOVED, AuditAction.DELETED]
    assert [entry.action for entry in audit] == [*in_trash, AuditAction.RESTORED]
    assert audit[-1].detail == "Restored to 04. Operational Handover"
    assert [entry.at for entry in audit[-2:]] == [START + timedelta(days=2), START + timedelta(days=3)]


def test_seeded_trash_items_can_be_restored_at_once(engine):
    assert [(a.asset_id, a.retention_days_left) for a in engine.snapshot().trash] == [
        ("AST-412", 24), ("AST-414", 9),
    ]

    engine.restore("AST-414")

    assert view(engine, "AST-414").stage == "FIELD_INSPECTION"


def test_purge_removes_only_assets_that_are_in_the_trash(engine):
    with pytest.raises(CommandRejected) as active:
        engine.purge("AST-401")
    engine.purge("AST-412")
    with pytest.raises(CommandRejected) as gone:
        engine.restore("AST-412")

    assert (active.value.status_code, gone.value.status_code) == (409, 404)
    assert "Only assets in the trash bin can be purged" in active.value.detail
    assert "AST-401" in active_ids(engine)
    assert trash_ids(engine) == ["AST-414"]
    assert engine.snapshot().activity[0].entry.action is AuditAction.PURGED


def test_wrong_state_commands_are_refused(engine):
    cases = [
        (engine.soft_delete, "AST-412", 409),  # already deleted
        (engine.restore, "AST-401", 409),  # not deleted
        (engine.soft_delete, "AST-999", 404),
        (engine.purge, "AST-999", 404),
    ]
    for command, asset_id, status in cases:
        with pytest.raises(CommandRejected) as rejected:
            command(asset_id)
        assert rejected.value.status_code == status
    assert engine.snapshot().sequence == 0


def test_retention_days_left_is_computed_from_the_clock(engine, clock):
    engine.soft_delete("AST-401")

    for elapsed, expected in [(0, 30), (1, 29), (12.5, 18), (29, 1), (29.9, 1)]:
        clock.now = START + timedelta(days=elapsed)
        assert view(engine, "AST-401").retention_days_left == expected


def test_asset_is_purged_on_the_first_read_after_retention_ends(engine, clock):
    engine.soft_delete("AST-401")
    clock.advance(days=30, seconds=-1)
    assert "AST-401" in trash_ids(engine)

    clock.advance(seconds=1)
    snapshot = engine.snapshot()

    # AST-412 and AST-414 were deleted before the start, so they expired earlier.
    assert snapshot.trash == []
    assert snapshot.kpis.trash_assets == 0
    assert snapshot.activity[0].entry.detail == "Purged after 30 days in the trash bin"
    with pytest.raises(CommandRejected) as rejected:
        engine.restore("AST-401")
    assert rejected.value.status_code == 404


def test_an_expired_asset_cannot_be_restored_even_before_any_read(engine, clock):
    clock.advance(days=9, seconds=1)  # AST-414 was deleted 21 days before the start

    with pytest.raises(CommandRejected) as rejected:
        engine.restore("AST-414")

    assert rejected.value.status_code == 404
    assert trash_ids(engine) == ["AST-412"]


def test_retention_period_is_configurable(clock):
    engine = build_engine(clock=clock, retention_days=7)

    # With 7 days, the two seeded items (deleted 6 and 21 days ago) differ at once.
    assert [(a.asset_id, a.retention_days_left) for a in engine.snapshot().trash] == [("AST-412", 1)]
    assert engine.snapshot().retention_days == 7
