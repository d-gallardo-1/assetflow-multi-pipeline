import { ChevronLeft, ChevronRight, Trash2 } from 'lucide-react';
import { formatArea, formatGbp, formatNumber } from '../../lib/format';
import type { Asset, StageInfo } from '../../types/portfolio';
import { CoordsBadge, PermitBadge, RiskBadge } from '../shared/Badges';

interface Props {
  asset: Asset;
  stages: StageInfo[];
  busy: boolean;
  onMove: (asset: Asset, stage: StageInfo) => void;
  onDelete: (asset: Asset) => void;
}

/**
 * One asset on the board. The previous and next buttons make every move
 * possible from the keyboard; each says where it leads.
 */
export function AssetCard({ asset, stages, busy, onMove, onDelete }: Props) {
  const previous = stages[asset.stage_index - 1];
  const next = stages[asset.stage_index + 1];
  const received = asset.document_checklist.filter((item) => item.received).length;

  return (
    <li>
      <article aria-label={`${asset.asset_id} ${asset.name}`} className="space-y-2 rounded-md border border-edge bg-obsidian p-2.5">
        <header>
          <p className="tag">{asset.asset_id}</p>
          <h4 className="text-sm font-medium text-slate-100">{asset.name}</h4>
          <p className="text-xs text-slate-400">
            {asset.region} · {asset.lead_engineer}
          </p>
        </header>

        <dl className="grid grid-cols-3 gap-1 text-xs">
          <div>
            <dt className="text-slate-400">Capital</dt>
            <dd className="font-mono text-slate-100" title={formatGbp(asset.capital_value_gbp)}>
              {formatGbp(asset.capital_value_gbp, true)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-400">Area</dt>
            <dd className="font-mono text-slate-100">{formatArea(asset.area_sqm)}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Grid</dt>
            <dd className="font-mono text-slate-100">{formatNumber(asset.grid_capacity_mva)} MVA</dd>
          </div>
        </dl>

        <p className="flex flex-wrap gap-1">
          <PermitBadge verified={asset.permits_verified} />
          <RiskBadge level={asset.risk_level} />
          <CoordsBadge coords={asset.gis_coords} />
        </p>
        <p className="text-xs text-slate-400">
          Documents on file: {received} of {asset.document_checklist.length}
        </p>

        <div className="flex items-center gap-1">
          <button
            type="button"
            className="btn px-2 py-1"
            disabled={busy || !previous}
            aria-label={previous ? `Move ${asset.asset_id} back to ${previous.label}` : `${asset.asset_id} is at the first stage`}
            onClick={() => previous && onMove(asset, previous)}
          >
            <ChevronLeft aria-hidden="true" className="h-4 w-4" />
          </button>
          <button
            type="button"
            className="btn px-2 py-1"
            disabled={busy || !next}
            aria-label={next ? `Move ${asset.asset_id} forward to ${next.label}` : `${asset.asset_id} is at the last stage`}
            onClick={() => next && onMove(asset, next)}
          >
            <ChevronRight aria-hidden="true" className="h-4 w-4" />
          </button>
          <button
            type="button"
            className="btn-danger ml-auto px-2 py-1"
            disabled={busy}
            aria-label={`Move ${asset.asset_id} to the trash bin`}
            onClick={() => onDelete(asset)}
          >
            <Trash2 aria-hidden="true" className="h-4 w-4" />
          </button>
        </div>
      </article>
    </li>
  );
}
