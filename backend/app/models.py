"""Domain models and the snapshot contract shared with the frontend."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class Pipeline(str, Enum):
    LAND_ACQUISITION = "LAND_ACQUISITION"
    BUILD_TO_SUIT = "BUILD_TO_SUIT"
    MULTI_TENANT_PARKS = "MULTI_TENANT_PARKS"
    ADVISORY_VALUATION = "ADVISORY_VALUATION"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AuditAction(str, Enum):
    CREATED = "CREATED"
    MOVED = "MOVED"
    DELETED = "DELETED"
    RESTORED = "RESTORED"
    #: Only ever seen in the activity feed: a purged asset has no trail left.
    PURGED = "PURGED"


class GisCoords(BaseModel):
    lat: float
    lon: float


class AuditEntry(BaseModel):
    at: datetime
    action: AuditAction
    detail: str = ""


class Asset(BaseModel):
    asset_id: str
    name: str
    pipeline: Pipeline
    stage: str
    region: str
    area_sqm: int
    #: Money is a Decimal end to end and travels as a JSON string, never a float.
    capital_value_gbp: Decimal
    lead_engineer: str
    gis_coords: GisCoords
    grid_capacity_mva: float
    permits_verified: bool
    risk_level: RiskLevel
    audit: list[AuditEntry] = Field(default_factory=list)
    #: The single source of truth for deletion: UTC time, ``None`` while active.
    deleted_at: datetime | None = None


# ---- read side -------------------------------------------------------------


class ChecklistItem(BaseModel):
    document: str
    stage_label: str
    received: bool


class AssetView(Asset):
    stage_index: int
    stage_label: str
    document_checklist: list[ChecklistItem]
    # Derived from ``deleted_at``, the retention period and the clock.
    is_deleted: bool
    retention_days_left: int | None = None
    purge_at: datetime | None = None


class StageInfo(BaseModel):
    code: str
    label: str


class PipelineBoard(BaseModel):
    pipeline: Pipeline
    label: str
    short_label: str
    stages: list[StageInfo]
    assets: list[AssetView]


class PipelineTotal(BaseModel):
    pipeline: Pipeline
    label: str
    asset_count: int
    capital_value_gbp: Decimal


class FunnelStep(BaseModel):
    """Assets at the n-th stage of their pipeline, across all four pipelines."""

    position: int
    asset_count: int
    capital_value_gbp: Decimal
    by_pipeline: dict[str, int]


class RiskTotal(BaseModel):
    risk_level: RiskLevel
    asset_count: int
    capital_value_gbp: Decimal


class Kpis(BaseModel):
    """Executive figures. Active assets only: the trash bin is never counted."""

    active_assets: int
    trash_assets: int
    total_capital_value_gbp: Decimal
    total_area_sqm: int
    total_grid_capacity_mva: float
    permits_verified: int
    capital_by_pipeline: list[PipelineTotal]
    funnel: list[FunnelStep]
    risk_distribution: list[RiskTotal]


class ActivityEntry(BaseModel):
    asset_id: str
    name: str
    entry: AuditEntry


class PortfolioSnapshot(BaseModel):
    sequence: int
    generated_at: datetime
    organisation: str
    retention_days: int
    pipelines: list[PipelineBoard]
    trash: list[AssetView]
    kpis: Kpis
    activity: list[ActivityEntry]
