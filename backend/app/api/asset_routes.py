"""Assets: create, bulk CSV import, downloads, stage moves and soft delete.

Static routes are declared before the parameterised ones, so a path such as
``/assets/reset`` can never be read as an asset id.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Request
from fastapi.responses import Response

from ..engine import PortfolioEngine
from ..exchange.csv_export import to_csv
from ..exchange.csv_import import MAX_CSV_BYTES, CsvRejected, parse_csv
from ..exchange.xlsx_export import portfolio_workbook
from ..intake import ASSET_ID_PATTERN, AssetInput
from ..seed import sample_inputs
from .schemas import AssetCreated, CommandAccepted, ImportReport, StageRequest

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
AssetId = Annotated[str, Path(pattern=ASSET_ID_PATTERN)]


async def read_limited(request: Request, limit: int) -> bytes:
    """Read the request body, refusing it as soon as it exceeds ``limit`` bytes."""
    too_large = CsvRejected(413, f"The file is larger than the {limit // 1024} KB limit.")
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise too_large
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise too_large
        chunks.append(chunk)
    return b"".join(chunks)


def _download(payload: bytes, media_type: str, filename: str) -> Response:
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=payload, media_type=media_type, headers=headers)


def build_asset_router(engine: PortfolioEngine) -> APIRouter:
    router = APIRouter(prefix="/assets", tags=["assets"])

    @router.post("", response_model=AssetCreated, status_code=201)
    async def create(body: AssetInput) -> AssetCreated:
        """Create one asset. Leave ``asset_id`` out and the server assigns it."""
        asset = engine.create(body)
        return AssetCreated(asset_id=asset.asset_id, sequence=engine.snapshot().sequence)

    @router.post("/reset", response_model=CommandAccepted)
    async def reset() -> CommandAccepted:
        """Back to the sixteen seed assets, two of them in the trash bin."""
        return CommandAccepted(sequence=engine.reset().sequence)

    @router.post("/import-csv", response_model=ImportReport)
    async def import_csv(request: Request) -> ImportReport:
        """Import a CSV sent as the raw request body (an uploaded file or pasted text)."""
        data = await read_limited(request, MAX_CSV_BYTES)
        active, trash = engine.taken_ids()
        parsed = parse_csv(data, active, trash)
        added = engine.add_many(parsed.valid)
        if added:
            engine.publish()
        return ImportReport(
            total_rows=parsed.total_rows,
            imported=[asset.asset_id for asset in added],
            rejected_rows=len({error.row for error in parsed.errors}),
            errors=parsed.errors,
        )

    @router.get("/sample-csv")
    async def sample_csv() -> Response:
        """The built-in batch of five synthetic assets, ready to import."""
        payload = to_csv(sample_inputs()).encode("utf-8")
        return _download(payload, "text/csv; charset=utf-8", "assetflow_sample_batch.csv")

    @router.get("/export-xlsx")
    async def export_xlsx() -> Response:
        """Active assets and the executive summary. The trash bin is not exported."""
        # One snapshot supplies both the figures and the timestamp, so they agree.
        snapshot = engine.snapshot()
        generated = snapshot.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        payload = portfolio_workbook(engine.active_assets(), snapshot.kpis, engine.organisation, generated)
        return _download(payload, XLSX_MEDIA_TYPE, "assetflow_portfolio.xlsx")

    @router.patch("/{asset_id}/stage", response_model=CommandAccepted)
    async def move(asset_id: AssetId, body: StageRequest) -> CommandAccepted:
        """Move an asset to another stage of its own pipeline."""
        return CommandAccepted(sequence=engine.move(asset_id, body.stage).sequence)

    @router.delete("/{asset_id}", response_model=CommandAccepted)
    async def soft_delete(asset_id: AssetId) -> CommandAccepted:
        """Soft delete: the asset moves to the trash bin and can be restored."""
        return CommandAccepted(sequence=engine.soft_delete(asset_id).sequence)

    return router


def build_trash_router(engine: PortfolioEngine) -> APIRouter:
    router = APIRouter(prefix="/trash", tags=["trash"])

    @router.post("/{asset_id}/restore", response_model=CommandAccepted)
    async def restore(asset_id: AssetId) -> CommandAccepted:
        """Back to the exact pipeline and stage the asset was deleted from."""
        return CommandAccepted(sequence=engine.restore(asset_id).sequence)

    @router.delete("/{asset_id}/purge", response_model=CommandAccepted)
    async def purge(asset_id: AssetId) -> CommandAccepted:
        """Permanent removal. Refused for an asset that is not in the trash bin."""
        return CommandAccepted(sequence=engine.purge(asset_id).sequence)

    return router
