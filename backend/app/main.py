"""FastAPI application (orchestrator): wires the engine, routers and error handlers.

Run with a single worker so the in-memory state is shared by every client::

    uvicorn app.main:app --host 127.0.0.1 --port 8003 --workers 1
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import __version__
from .api.asset_routes import build_asset_router, build_trash_router
from .api.read_routes import build_read_router
from .config import API_PREFIX, Settings, load_settings
from .data.portfolio import ORGANISATION
from .engine import CommandRejected, PortfolioEngine, utc_now
from .exchange.csv_import import CsvRejected
from .seed import default_assets


def build_engine(
    *, clock: Callable[[], datetime] = utc_now, retention_days: int = 30
) -> PortfolioEngine:
    return PortfolioEngine(
        default_assets, organisation=ORGANISATION, retention_days=retention_days, clock=clock
    )


def create_app(engine: PortfolioEngine | None = None, *, settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    engine = engine or build_engine(retention_days=settings.retention_days)

    app = FastAPI(
        title="AssetFlow Multi-Pipeline API",
        version=__version__,
        description=(
            "Reference demo. The organisation, every asset, site name, engineer and figure "
            "is invented; the service is not connected to any real system."
        ),
        # The interactive docs page loads its assets from a public CDN, which
        # would break the offline, on-premises promise. The schema stays available.
        docs_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json",
        redoc_url=None,
    )
    app.state.engine = engine

    @app.exception_handler(CommandRejected)
    @app.exception_handler(CsvRejected)
    async def refused(_: Request, exc: CommandRejected | CsvRejected) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(
        build_read_router(engine, heartbeat_seconds=settings.heartbeat_seconds), prefix=API_PREFIX
    )
    app.include_router(build_asset_router(engine), prefix=API_PREFIX)
    app.include_router(build_trash_router(engine), prefix=API_PREFIX)
    return app


app = create_app()
