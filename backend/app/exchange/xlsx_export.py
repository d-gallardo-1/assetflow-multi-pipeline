"""Portfolio workbook: active assets and the executive summary."""

from __future__ import annotations

import io
from typing import Iterable, Sequence

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from ..models import Asset, Kpis
from ..pipelines import SPECS, stage_label
from .safe_text import neutralise

ASSET_HEADERS = (
    "Asset ID", "Name", "Pipeline", "Stage", "Region", "Area (sqm)", "Capital value (GBP)",
    "Lead engineer", "Latitude", "Longitude", "Grid capacity (MVA)", "Permits verified", "Risk level",
)
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="1F2937")


def write_sheet(sheet: Worksheet, headers: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    """Header row plus data rows. Text is neutralised and stored as a literal
    string, so nothing taken from user input is written back as a live formula."""
    widths = [len(header) for header in headers]
    for column, header in enumerate(headers, start=1):
        cell = sheet.cell(row=1, column=column, value=header)
        cell.font, cell.fill = _HEADER_FONT, _HEADER_FILL
    for row_index, row in enumerate(rows, start=2):
        for column, value in enumerate(row, start=1):
            text = neutralise(value) if isinstance(value, str) else value
            cell = sheet.cell(row=row_index, column=column, value=text)
            if isinstance(text, str):
                cell.data_type = "s"
                widths[column - 1] = max(widths[column - 1], len(text))
    for column, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(column)].width = min(width + 2, 60)
    sheet.freeze_panes = "A2"


def _asset_row(asset: Asset) -> tuple[object, ...]:
    spec = SPECS[asset.pipeline]
    index = spec.index_of(asset.stage) or 0
    return (
        asset.asset_id, asset.name, spec.label, stage_label(index, spec.stages[index]), asset.region,
        asset.area_sqm, asset.capital_value_gbp, asset.lead_engineer, asset.gis_coords.lat,
        asset.gis_coords.lon, asset.grid_capacity_mva, "Yes" if asset.permits_verified else "No",
        asset.risk_level.value,
    )


def _summary_rows(organisation: str, generated: str, kpis: Kpis) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = [
        ("Organisation", organisation, ""),
        ("Generated at", generated, ""),
        ("Active assets", kpis.active_assets, kpis.total_capital_value_gbp),
        ("Total managed area (sqm)", kpis.total_area_sqm, ""),
        ("Total grid capacity (MVA)", kpis.total_grid_capacity_mva, ""),
        ("Assets with permits verified", kpis.permits_verified, ""),
    ]
    rows += [(f"Pipeline: {t.label}", t.asset_count, t.capital_value_gbp) for t in kpis.capital_by_pipeline]
    rows += [(f"Funnel: stage {s.position}", s.asset_count, s.capital_value_gbp) for s in kpis.funnel]
    rows += [(f"Risk: {r.risk_level.value}", r.asset_count, r.capital_value_gbp) for r in kpis.risk_distribution]
    return rows


def portfolio_workbook(active: Sequence[Asset], kpis: Kpis, organisation: str, generated: str) -> bytes:
    """``active`` and ``kpis`` must describe the same state. The trash bin is left out."""
    workbook = Workbook()
    assets = workbook.active
    assets.title = "Assets"
    write_sheet(assets, ASSET_HEADERS, [_asset_row(a) for a in sorted(active, key=lambda a: a.asset_id)])
    write_sheet(
        workbook.create_sheet("Summary"), ("Measure", "Count", "Capital value (GBP)"),
        _summary_rows(organisation, generated, kpis),
    )
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
