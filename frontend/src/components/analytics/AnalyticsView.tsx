import { Download } from 'lucide-react';
import type { ReactNode } from 'react';
import { api } from '../../lib/api';
import { formatArea, formatGbp, formatNumber, percentOf } from '../../lib/format';
import type { Kpis, RiskLevel } from '../../types/portfolio';
import { RiskBadge, riskTone } from '../shared/Badges';
import { BarList, type BarRow } from './BarList';

function Panel({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <section className="panel space-y-3 p-4" aria-label={title}>
      <h3 className="panel-title">{title}</h3>
      {children}
      {note && <p className="text-xs text-slate-400">{note}</p>}
    </section>
  );
}

/** Executive portfolio analytics. Every figure comes from the backend and counts active assets only. */
export function AnalyticsView({ kpis }: { kpis: Kpis }) {
  const total = Number(kpis.total_capital_value_gbp);
  const count = (assets: number) => `${assets} ${assets === 1 ? 'asset' : 'assets'}`;

  const byPipeline: BarRow[] = kpis.capital_by_pipeline.map((row) => ({
    key: row.pipeline,
    label: `${row.label} (${count(row.asset_count)})`,
    value: formatGbp(row.capital_value_gbp, true),
    percent: percentOf(Number(row.capital_value_gbp), total),
  }));
  const funnel: BarRow[] = kpis.funnel.map((step) => ({
    key: String(step.position),
    label: `Stage ${step.position} (${formatGbp(step.capital_value_gbp, true)})`,
    value: count(step.asset_count),
    percent: percentOf(step.asset_count, kpis.active_assets),
  }));
  const risks: BarRow[] = kpis.risk_distribution.map((row) => ({
    key: row.risk_level,
    label: <RiskBadge level={row.risk_level} />,
    value: `${count(row.asset_count)} · ${formatGbp(row.capital_value_gbp, true)}`,
    percent: percentOf(row.asset_count, kpis.active_assets),
  }));

  return (
    <section className="space-y-4" aria-label="Executive portfolio analytics">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-300">
          {count(kpis.active_assets)} under management, worth{' '}
          <span className="font-mono text-slate-100">{formatGbp(kpis.total_capital_value_gbp)}</span>. Assets in the
          trash bin are not counted.
        </p>
        <a className="btn" href={api.exportXlsxUrl} download>
          <Download aria-hidden="true" className="h-4 w-4" />
          Export portfolio (.xlsx)
        </a>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Capital value by pipeline">
          <BarList caption="Capital value by pipeline" rows={byPipeline} />
        </Panel>
        <Panel
          title="Funnel across stages"
          note="Stage 1 to 4 of each asset's own pipeline, all four pipelines together."
        >
          <BarList caption="Funnel across stages" rows={funnel} tone="nominal" />
        </Panel>
        <Panel title="Risk distribution">
          <BarList
            caption="Risk distribution"
            rows={risks}
            tone={(row) => riskTone(row.key as RiskLevel)}
          />
        </Panel>
        <Panel title="Portfolio totals">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {[
              ['Total managed area', formatArea(kpis.total_area_sqm)],
              ['Total grid capacity', `${formatNumber(kpis.total_grid_capacity_mva)} MVA`],
              ['Permits verified', `${kpis.permits_verified} of ${kpis.active_assets}`],
              ['In the trash bin', count(kpis.trash_assets)],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-slate-400">{label}</dt>
                <dd className="font-mono text-lg text-slate-100">{value}</dd>
              </div>
            ))}
          </dl>
        </Panel>
      </div>
    </section>
  );
}
