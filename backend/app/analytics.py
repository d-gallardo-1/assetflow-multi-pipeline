"""Executive KPIs. Every figure is computed from active assets only."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from .models import Asset, FunnelStep, Kpis, PipelineTotal, RiskLevel, RiskTotal
from .pipelines import SPECS, STAGES_PER_PIPELINE

ZERO = Decimal("0.00")


def _capital(assets: Sequence[Asset]) -> Decimal:
    return sum((asset.capital_value_gbp for asset in assets), ZERO)


def kpis(active: Sequence[Asset], trash_count: int) -> Kpis:
    funnel = []
    for position in range(STAGES_PER_PIPELINE):
        at_position = [a for a in active if SPECS[a.pipeline].index_of(a.stage) == position]
        funnel.append(
            FunnelStep(
                position=position + 1,
                asset_count=len(at_position),
                capital_value_gbp=_capital(at_position),
                by_pipeline={
                    spec.pipeline.value: sum(1 for a in at_position if a.pipeline is spec.pipeline)
                    for spec in SPECS.values()
                },
            )
        )

    by_pipeline = []
    for spec in SPECS.values():
        members = [a for a in active if a.pipeline is spec.pipeline]
        by_pipeline.append(
            PipelineTotal(
                pipeline=spec.pipeline, label=spec.short_label,
                asset_count=len(members), capital_value_gbp=_capital(members),
            )
        )

    risks = []
    for level in RiskLevel:
        members = [a for a in active if a.risk_level is level]
        risks.append(RiskTotal(risk_level=level, asset_count=len(members), capital_value_gbp=_capital(members)))

    return Kpis(
        active_assets=len(active),
        trash_assets=trash_count,
        total_capital_value_gbp=_capital(active),
        total_area_sqm=sum(a.area_sqm for a in active),
        total_grid_capacity_mva=round(sum(a.grid_capacity_mva for a in active), 3),
        permits_verified=sum(1 for a in active if a.permits_verified),
        capital_by_pipeline=by_pipeline,
        funnel=funnel,
        risk_distribution=risks,
    )
