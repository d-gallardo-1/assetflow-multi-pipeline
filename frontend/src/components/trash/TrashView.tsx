import { RotateCcw, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useAction } from '../../hooks/useAction';
import { api } from '../../lib/api';
import { formatGbp, formatUtc } from '../../lib/format';
import type { Asset, PipelineBoard } from '../../types/portfolio';
import { RetentionBadge } from '../shared/Badges';
import { ErrorNote } from '../shared/ErrorNote';

interface Props {
  trash: Asset[];
  pipelines: PipelineBoard[];
  retentionDays: number;
}

function AuditTrail({ asset }: { asset: Asset }) {
  return (
    <ol aria-label={`Audit trail of ${asset.asset_id}`} className="space-y-1">
      {asset.audit.map((entry, index) => (
        <li key={index} className="text-xs text-slate-300">
          <span className="font-mono text-slate-400">{formatUtc(entry.at)}</span> {entry.action}
          {entry.detail ? `: ${entry.detail}` : ''}
        </li>
      ))}
    </ol>
  );
}

/** Soft-delete trash bin and audit vault: what was deleted, when, how long it stays, and its history. */
export function TrashView({ trash, pipelines, retentionDays }: Props) {
  const { pending, error, run } = useAction();
  // Purging cannot be undone, so it takes a second, explicit press.
  const [confirming, setConfirming] = useState<string | null>(null);
  const labelOf = (asset: Asset) => pipelines.find((board) => board.pipeline === asset.pipeline)?.short_label ?? asset.pipeline;

  const purge = async (assetId: string) => {
    await run(assetId, () => api.purge(assetId));
    // Only the confirmation of this asset closes: another may have been opened meanwhile.
    setConfirming((current) => (current === assetId ? null : current));
  };

  return (
    <section className="panel space-y-3 p-4" aria-label="Soft-delete trash bin and audit vault">
      <h2 className="panel-title">Trash bin and audit vault ({trash.length})</h2>
      <p className="text-sm text-slate-400">
        A deleted asset leaves the board and the KPIs but keeps its audit trail. It can be restored to its exact
        pipeline and stage for {retentionDays} days; after that it is purged automatically.
      </p>
      <ErrorNote message={error} />
      {trash.length === 0 ? (
        <p className="text-sm text-slate-300">The trash bin is empty.</p>
      ) : (
        <ul className="space-y-3">
          {trash.map((asset) => {
            const busy = pending.has(asset.asset_id);
            return (
              <li key={asset.asset_id}>
                <article aria-label={`${asset.asset_id} in the trash bin`} className="rounded-md border border-edge bg-obsidian p-3">
                  <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
                    <div className="min-w-0 flex-1">
                      <p className="flex flex-wrap items-center gap-2">
                        <span className="tag">{asset.asset_id}</span>
                        <RetentionBadge daysLeft={asset.retention_days_left} />
                      </p>
                      <h3 className="text-sm font-medium text-slate-100">{asset.name}</h3>
                      <p className="text-xs text-slate-400">
                        {labelOf(asset)} · {asset.stage_label} · {formatGbp(asset.capital_value_gbp, true)}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        Deleted {formatUtc(asset.deleted_at)} · purged automatically {formatUtc(asset.purge_at)}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="btn-primary whitespace-nowrap"
                        disabled={busy}
                        aria-label={`Restore ${asset.asset_id} to ${labelOf(asset)}, ${asset.stage_label}`}
                        onClick={() => void run(asset.asset_id, () => api.restore(asset.asset_id))}
                      >
                        <RotateCcw aria-hidden="true" className="h-4 w-4" />
                        Restore to Pipeline
                      </button>
                      {confirming === asset.asset_id ? (
                        <>
                          <button type="button" className="btn-danger whitespace-nowrap" disabled={busy} onClick={() => void purge(asset.asset_id)}>
                            Confirm purge of {asset.asset_id}
                          </button>
                          <button type="button" className="btn" onClick={() => setConfirming(null)}>
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          className="btn-danger whitespace-nowrap"
                          disabled={busy}
                          aria-label={`Permanent purge of ${asset.asset_id}`}
                          onClick={() => setConfirming(asset.asset_id)}
                        >
                          <Trash2 aria-hidden="true" className="h-4 w-4" />
                          Permanent Purge
                        </button>
                      )}
                    </div>
                  </div>
                  {confirming === asset.asset_id && (
                    <p role="alert" className="mt-2 text-sm text-critical">
                      Purging removes {asset.asset_id} and its audit trail for good. This cannot be undone.
                    </p>
                  )}
                  <div className="mt-2 border-t border-edge pt-2">
                    <AuditTrail asset={asset} />
                  </div>
                </article>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
