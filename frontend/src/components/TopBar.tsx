import { BarChart3, FileUp, KanbanSquare, Trash2, type LucideIcon } from 'lucide-react';
import { formatArea, formatGbp, formatNumber } from '../lib/format';
import type { Kpis, StreamStatus, ViewId } from '../types/portfolio';
import { StreamBadge } from './shared/Badges';

interface Props {
  organisation: string | null;
  streamStatus: StreamStatus;
  kpis: Kpis | null;
  view: ViewId;
  onViewChange: (view: ViewId) => void;
}

const VIEWS: { id: ViewId; label: string; icon: LucideIcon }[] = [
  { id: 'board', label: 'Kanban Board', icon: KanbanSquare },
  { id: 'analytics', label: 'Portfolio Analytics', icon: BarChart3 },
  { id: 'ingest', label: 'CSV Ingestion', icon: FileUp },
  { id: 'trash', label: 'Trash Bin & Audit Vault', icon: Trash2 },
];

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel px-3 py-2">
      <dt className="panel-title">{label}</dt>
      <dd className="font-mono text-lg font-semibold text-slate-100">{value}</dd>
    </div>
  );
}

export function TopBar({ organisation, streamStatus, kpis, view, onViewChange }: Props) {
  return (
    <header className="border-b border-edge bg-panel/60">
      <div className="mx-auto max-w-[1600px] space-y-3 px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <div className="min-w-0">
            <h1 className="text-lg font-semibold text-slate-100">AssetFlow Multi-Pipeline</h1>
            <p className="truncate text-xs text-slate-400">{organisation ?? 'Loading portfolio…'}</p>
          </div>
          <span className="rounded border border-edge px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-400">
            Synthetic demo data
          </span>
          <div className="ml-auto">
            <StreamBadge status={streamStatus} />
          </div>
        </div>

        {kpis && (
          <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            <Kpi label="Active assets" value={String(kpis.active_assets)} />
            <Kpi label="Capital under management" value={formatGbp(kpis.total_capital_value_gbp, true)} />
            <Kpi label="Managed area" value={formatArea(kpis.total_area_sqm)} />
            <Kpi label="Grid capacity" value={`${formatNumber(kpis.total_grid_capacity_mva)} MVA`} />
            <Kpi label="In trash bin" value={String(kpis.trash_assets)} />
          </dl>
        )}

        <nav aria-label="Views" className="flex flex-wrap gap-2">
          {VIEWS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              aria-current={view === id ? 'page' : undefined}
              onClick={() => onViewChange(id)}
              className={`btn ${view === id ? 'border-link/60 bg-link/10 text-link' : ''}`}
            >
              <Icon aria-hidden="true" className="h-4 w-4" />
              {label}
              {id === 'trash' && kpis && kpis.trash_assets > 0 ? ` (${kpis.trash_assets})` : ''}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}
