"""Read side: turns stored assets into the views carried by a snapshot."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Iterable

from .models import Asset, AssetView, ChecklistItem, PipelineBoard, StageInfo
from .pipelines import SPECS, stage_label

_DAY_SECONDS = 86_400


def purge_time(asset: Asset, retention_days: int) -> datetime | None:
    if asset.deleted_at is None:
        return None
    return asset.deleted_at + timedelta(days=retention_days)


def is_expired(asset: Asset, retention_days: int, now: datetime) -> bool:
    due = purge_time(asset, retention_days)
    return due is not None and due <= now


def asset_view(asset: Asset, now: datetime, retention_days: int) -> AssetView:
    spec = SPECS[asset.pipeline]
    index = spec.index_of(asset.stage) or 0
    due = purge_time(asset, retention_days)
    days_left = None
    if due is not None:
        # Rounded up: an asset with two hours left still shows one day, never zero.
        days_left = max(0, math.ceil((due - now).total_seconds() / _DAY_SECONDS))
    return AssetView(
        **asset.model_dump(),
        stage_index=index,
        stage_label=stage_label(index, spec.stages[index]),
        # One record per stage, on file once the asset has reached that stage.
        document_checklist=[
            ChecklistItem(document=stage.document, stage_label=stage_label(i, stage), received=i <= index)
            for i, stage in enumerate(spec.stages)
        ],
        is_deleted=asset.deleted_at is not None,
        retention_days_left=days_left,
        purge_at=due,
    )


def boards(active: Iterable[AssetView]) -> list[PipelineBoard]:
    """Active assets grouped by pipeline, in id order."""
    active = sorted(active, key=lambda asset: asset.asset_id)
    return [
        PipelineBoard(
            pipeline=spec.pipeline,
            label=spec.label,
            short_label=spec.short_label,
            stages=[StageInfo(code=s.code, label=stage_label(i, s)) for i, s in enumerate(spec.stages)],
            assets=[asset for asset in active if asset.pipeline is spec.pipeline],
        )
        for spec in SPECS.values()
    ]


def trash_views(deleted: Iterable[AssetView]) -> list[AssetView]:
    """Most recent deletion first."""
    return sorted(deleted, key=lambda asset: (asset.deleted_at, asset.asset_id), reverse=True)
