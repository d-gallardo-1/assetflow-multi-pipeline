"""Assembles the built-in synthetic portfolio (orchestrator)."""

from __future__ import annotations

from datetime import datetime, timedelta

from .data.land_and_build import BUILD_TO_SUIT, LAND_ACQUISITION
from .data.parks_and_advisory import ADVISORY_VALUATION, DELETED_DAYS_AGO, MULTI_TENANT_PARKS
from .data.sample_batch import SAMPLE_BATCH
from .intake import AssetInput
from .models import Asset, AuditAction, AuditEntry, GisCoords, Pipeline

_FIELDS = (
    "asset_id", "name", "stage", "region", "area_sqm", "capital_value_gbp",
    "lead_engineer", "lat", "lon", "grid_capacity_mva", "permits_verified", "risk_level",
)
_BY_PIPELINE = {
    Pipeline.LAND_ACQUISITION: LAND_ACQUISITION,
    Pipeline.BUILD_TO_SUIT: BUILD_TO_SUIT,
    Pipeline.MULTI_TENANT_PARKS: MULTI_TENANT_PARKS,
    Pipeline.ADVISORY_VALUATION: ADVISORY_VALUATION,
}


def default_assets(now: datetime) -> list[Asset]:
    """The sixteen seed assets. Each passes the same validation as an imported
    row, and two of them start in the trash bin, deleted some days before ``now``."""
    assets = []
    for pipeline, rows in _BY_PIPELINE.items():
        for row in rows:
            data = AssetInput(pipeline=pipeline, **dict(zip(_FIELDS, row)))
            created = AuditEntry(at=now - timedelta(days=45), action=AuditAction.CREATED, detail="Seed portfolio")
            asset = Asset(
                **data.model_dump(exclude={"lat", "lon"}),
                gis_coords=GisCoords(lat=data.lat, lon=data.lon), audit=[created],
            )
            days = DELETED_DAYS_AGO.get(asset.asset_id)
            if days is not None:
                asset.deleted_at = now - timedelta(days=days)
                asset.audit.append(
                    AuditEntry(at=asset.deleted_at, action=AuditAction.DELETED, detail="Moved to the trash bin")
                )
            assets.append(asset)
    return assets


def sample_inputs() -> list[AssetInput]:
    fields = ("asset_id", "name", "pipeline", "stage", *_FIELDS[3:])
    return [AssetInput(**dict(zip(fields, row))) for row in SAMPLE_BATCH]
