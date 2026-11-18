"""PortfolioEngine (orchestrator): owns all mutable state and enforces every rule.

Each command validates, mutates, writes the audit entry and publishes one full
snapshot. A refused command raises ``CommandRejected`` and changes nothing.
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from typing import Callable, Iterable

from .analytics import kpis
from .broadcaster import Broadcaster
from .errors import CommandRejected, utc_now
from .intake import AssetInput, next_asset_id
from .models import ActivityEntry, Asset, AuditAction, AuditEntry, GisCoords, PortfolioSnapshot
from .pipelines import SPECS, stage_code, stage_label
from .views import asset_view, boards, is_expired, trash_views

__all__ = ["CommandRejected", "PortfolioEngine", "utc_now"]

ACTIVITY_SIZE = 30

Seed = Callable[[datetime], list[Asset]]


class PortfolioEngine:
    def __init__(
        self, seed: Seed, *, organisation: str, retention_days: int = 30,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.organisation = organisation
        self.retention_days = retention_days
        self._seed = seed
        self._clock = clock
        self._broadcaster = Broadcaster()
        self._sequence = 0
        self._activity: deque[ActivityEntry] = deque(maxlen=ACTIVITY_SIZE)
        self._assets: dict[str, Asset] = {}
        self._load()

    # ---- stream and read side ----------------------------------------------

    @property
    def subscriber_count(self) -> int:
        return self._broadcaster.subscriber_count

    def subscribe(self) -> asyncio.Queue[PortfolioSnapshot]:
        return self._broadcaster.subscribe()

    def unsubscribe(self, queue: asyncio.Queue[PortfolioSnapshot]) -> None:
        self._broadcaster.unsubscribe(queue)

    def snapshot(self) -> PortfolioSnapshot:
        now = self._now()
        active = self.active_assets()
        views = [asset_view(asset, now, self.retention_days) for asset in self._assets.values()]
        return PortfolioSnapshot(
            sequence=self._sequence,
            generated_at=now,
            organisation=self.organisation,
            retention_days=self.retention_days,
            pipelines=boards(view for view in views if not view.is_deleted),
            trash=trash_views(view for view in views if view.is_deleted),
            kpis=kpis(active, len(self._assets) - len(active)),
            activity=list(self._activity),
        )

    def publish(self) -> PortfolioSnapshot:
        self._sequence += 1
        snapshot = self.snapshot()
        self._broadcaster.publish(snapshot)
        return snapshot

    def active_assets(self) -> list[Asset]:
        return [asset for asset in self._assets.values() if asset.deleted_at is None]

    def taken_ids(self) -> tuple[set[str], set[str]]:
        """Ids in use as ``(active, trash)``: neither may be overwritten."""
        self._now()
        trash = {a.asset_id for a in self._assets.values() if a.deleted_at is not None}
        return set(self._assets) - trash, trash

    # ---- commands ----------------------------------------------------------

    def create(self, data: AssetInput) -> Asset:
        asset = self.add_many([data])[0]
        self.publish()
        return asset

    def add_many(self, inputs: Iterable[AssetInput]) -> list[Asset]:
        """Add validated assets without publishing; the caller publishes once."""
        now = self._now()
        added = []
        # Rows that bring their own id go first, so an assigned id never takes one.
        for data in sorted(inputs, key=lambda row: row.asset_id is None):
            asset_id = data.asset_id or next_asset_id(self._assets)
            if asset_id in self._assets:
                raise CommandRejected(409, f"{asset_id} already exists.")
            asset = Asset(
                **data.model_dump(exclude={"asset_id", "lat", "lon"}), asset_id=asset_id,
                gis_coords=GisCoords(lat=round(data.lat, 4), lon=round(data.lon, 4)),
            )
            self._assets[asset_id] = asset
            self._record(asset, AuditAction.CREATED, now, f"Created at {self._stage_text(asset)}")
            added.append(asset)
        return added

    def move(self, asset_id: str, stage: str) -> PortfolioSnapshot:
        now = self._now()
        asset = self._find(asset_id)
        if asset.deleted_at is not None:
            raise CommandRejected(409, f"{asset_id} is in the trash bin; restore it before moving it.")
        spec = SPECS[asset.pipeline]
        code = stage_code(stage)
        if spec.index_of(code) is None:
            allowed = ", ".join(s.code for s in spec.stages)
            raise CommandRejected(
                422, f"'{stage}' is not a stage of {asset.pipeline.value}. Expected one of: {allowed}."
            )
        if code == asset.stage:
            raise CommandRejected(409, f"{asset_id} is already at {self._stage_text(asset)}.")
        before = self._stage_text(asset)
        asset.stage = code
        self._record(asset, AuditAction.MOVED, now, f"{before} to {self._stage_text(asset)}")
        return self.publish()

    def soft_delete(self, asset_id: str) -> PortfolioSnapshot:
        now = self._now()
        asset = self._find(asset_id)
        if asset.deleted_at is not None:
            raise CommandRejected(409, f"{asset_id} is already in the trash bin.")
        asset.deleted_at = now
        self._record(asset, AuditAction.DELETED, now, f"Moved to the trash bin from {self._stage_text(asset)}")
        return self.publish()

    def restore(self, asset_id: str) -> PortfolioSnapshot:
        now = self._now()
        asset = self._find(asset_id)
        if asset.deleted_at is None:
            raise CommandRejected(409, f"{asset_id} is not in the trash bin.")
        asset.deleted_at = None
        self._record(asset, AuditAction.RESTORED, now, f"Restored to {self._stage_text(asset)}")
        return self.publish()

    def purge(self, asset_id: str) -> PortfolioSnapshot:
        now = self._now()
        asset = self._find(asset_id)
        if asset.deleted_at is None:
            raise CommandRejected(409, f"{asset_id} is active. Only assets in the trash bin can be purged.")
        self._remove(asset, now, "Purged permanently on request")
        return self.publish()

    def reset(self) -> PortfolioSnapshot:
        self._load()
        return self.publish()

    # ---- internals ---------------------------------------------------------

    def _load(self) -> None:
        self._activity.clear()
        self._assets = {asset.asset_id: asset for asset in self._seed(self._clock())}

    def _now(self) -> datetime:
        """The current time. Reading it also purges what has outlived its retention,
        so no read and no command ever sees an expired asset."""
        now = self._clock()
        for asset in [a for a in self._assets.values() if is_expired(a, self.retention_days, now)]:
            self._remove(asset, now, f"Purged after {self.retention_days} days in the trash bin")
        return now

    def _remove(self, asset: Asset, now: datetime, detail: str) -> None:
        del self._assets[asset.asset_id]
        entry = AuditEntry(at=now, action=AuditAction.PURGED, detail=detail)
        self._activity.appendleft(ActivityEntry(asset_id=asset.asset_id, name=asset.name, entry=entry))

    def _find(self, asset_id: str) -> Asset:
        asset = self._assets.get(asset_id)
        if asset is None:
            raise CommandRejected(404, f"{asset_id} does not exist.")
        return asset

    @staticmethod
    def _stage_text(asset: Asset) -> str:
        spec = SPECS[asset.pipeline]
        index = spec.index_of(asset.stage) or 0
        return stage_label(index, spec.stages[index])

    def _record(self, asset: Asset, action: AuditAction, now: datetime, detail: str) -> None:
        entry = AuditEntry(at=now, action=action, detail=detail)
        asset.audit.append(entry)
        self._activity.appendleft(ActivityEntry(asset_id=asset.asset_id, name=asset.name, entry=entry))
