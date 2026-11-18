import { useState } from 'react';
import { useAction } from '../../hooks/useAction';
import { api } from '../../lib/api';
import type { Asset, Pipeline, PipelineBoard, StageInfo } from '../../types/portfolio';
import { ErrorNote } from '../shared/ErrorNote';
import { AssetCard } from './AssetCard';

interface Props {
  pipelines: PipelineBoard[];
  retentionDays: number;
}

/** Board view (orchestrator): one pipeline at a time, a column per stage. */
export function KanbanBoard({ pipelines, retentionDays }: Props) {
  const [selected, setSelected] = useState<Pipeline | null>(null);
  const { pending, error, run } = useAction();
  const board = pipelines.find((candidate) => candidate.pipeline === selected) ?? pipelines[0];
  if (!board) return null;

  const move = (asset: Asset, stage: StageInfo) => run(asset.asset_id, () => api.moveStage(asset.asset_id, stage.code));
  const remove = (asset: Asset) => run(asset.asset_id, () => api.softDelete(asset.asset_id));

  return (
    <section className="space-y-3" aria-label="Multi-pipeline Kanban board">
      <div role="tablist" aria-label="Pipelines" className="flex flex-wrap gap-2">
        {pipelines.map((candidate) => (
          <button
            key={candidate.pipeline}
            type="button"
            role="tab"
            aria-selected={candidate.pipeline === board.pipeline}
            onClick={() => setSelected(candidate.pipeline)}
            className={`btn ${candidate.pipeline === board.pipeline ? 'border-link/60 bg-link/10 text-link' : ''}`}
          >
            {candidate.short_label}
            <span className="font-mono text-xs text-slate-400">{candidate.assets.length}</span>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-100">{board.label}</h2>
        <p className="text-xs text-slate-400">
          Deleting moves an asset to the trash bin, where it can be restored for {retentionDays} days.
        </p>
      </div>
      <ErrorNote message={error} />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {board.stages.map((stage, index) => {
          const inStage = board.assets.filter((asset) => asset.stage_index === index);
          return (
            <section key={stage.code} aria-label={stage.label} className="panel p-2.5">
              <h3 className="mb-2 flex items-baseline justify-between gap-2">
                <span className="font-mono text-xs font-semibold tracking-wide text-slate-200">{stage.label}</span>
                <span className="font-mono text-xs text-slate-400">{inStage.length}</span>
              </h3>
              {inStage.length === 0 ? (
                <p className="rounded-md border border-dashed border-edge px-2 py-4 text-center text-xs text-slate-400">
                  No assets at this stage
                </p>
              ) : (
                <ul className="space-y-2">
                  {inStage.map((asset) => (
                    <AssetCard
                      key={asset.asset_id}
                      asset={asset}
                      stages={board.stages}
                      busy={pending.has(asset.asset_id)}
                      onMove={(target, to) => void move(target, to)}
                      onDelete={(target) => void remove(target)}
                    />
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </div>
    </section>
  );
}
