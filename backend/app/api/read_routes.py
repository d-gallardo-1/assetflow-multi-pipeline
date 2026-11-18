"""Read side: health, state snapshot and the SSE stream."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from .. import __version__
from ..engine import PortfolioEngine
from ..models import PortfolioSnapshot
from ..sse import event_stream
from .schemas import Health


def build_read_router(engine: PortfolioEngine, *, heartbeat_seconds: float) -> APIRouter:
    router = APIRouter(tags=["read"])

    @router.get("/health", response_model=Health)
    async def health() -> Health:
        return Health(
            status="ok",
            version=__version__,
            synthetic_data=True,
            subscribers=engine.subscriber_count,
        )

    @router.get("/state", response_model=PortfolioSnapshot)
    async def state() -> PortfolioSnapshot:
        return engine.snapshot()

    @router.get("/stream")
    async def stream(
        max_events: Annotated[
            int | None,
            Query(ge=1, le=1000, description="Close the stream after N events (useful with curl)."),
        ] = None,
    ) -> StreamingResponse:
        return StreamingResponse(
            event_stream(engine, max_events=max_events, heartbeat_seconds=heartbeat_seconds),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                # Tells Nginx not to buffer this response.
                "X-Accel-Buffering": "no",
            },
        )

    return router
