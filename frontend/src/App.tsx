import { useState } from 'react';
import { AnalyticsView } from './components/analytics/AnalyticsView';
import { KanbanBoard } from './components/board/KanbanBoard';
import { IngestView } from './components/ingest/IngestView';
import { TopBar } from './components/TopBar';
import { TrashView } from './components/trash/TrashView';
import { usePortfolioStream } from './hooks/usePortfolioStream';
import type { ViewId } from './types/portfolio';

/** Application shell (orchestrator): one SSE subscription feeds every view. */
export default function App() {
  const { snapshot, status } = usePortfolioStream();
  const [view, setView] = useState<ViewId>('board');
  const offline = status === 'DISCONNECTED';

  return (
    <div className="min-h-screen">
      <TopBar
        organisation={snapshot?.organisation ?? null}
        streamStatus={status}
        kpis={snapshot?.kpis ?? null}
        view={view}
        onViewChange={setView}
      />

      <main className="mx-auto max-w-[1600px] space-y-4 px-4 py-4">
        {!snapshot && (
          <p className="panel p-4 text-sm text-slate-300" role="status">
            {offline
              ? 'Cannot reach the backend. Retrying every few seconds; check that the API is running on port 8003.'
              : 'Waiting for the first portfolio snapshot…'}
          </p>
        )}

        {snapshot && status !== 'CONNECTED' && (
          <p role="alert" className="rounded-md border border-warn/50 bg-warn/10 px-3 py-2 text-sm text-warn">
            {offline
              ? 'Live connection lost. The data below is the last snapshot received and may be out of date; controls are disabled until the stream is back.'
              : 'Reconnecting to the live stream. The data below may be a few seconds old.'}
          </p>
        )}

        {snapshot && (
          // A disabled fieldset disables every form control inside it. That is
          // deliberate once the connection is given up on: a command sent from
          // a stale screen could act on a stage that has already changed.
          <fieldset disabled={offline} className="m-0 min-w-0 border-0 p-0">
            {view === 'board' && (
              <KanbanBoard pipelines={snapshot.pipelines} retentionDays={snapshot.retention_days} />
            )}
            {view === 'analytics' && <AnalyticsView kpis={snapshot.kpis} />}
            {/* Kept mounted so the validation log survives a look at another view. */}
            <div hidden={view !== 'ingest'}>
              <IngestView />
            </div>
            {view === 'trash' && (
              <TrashView trash={snapshot.trash} pipelines={snapshot.pipelines} retentionDays={snapshot.retention_days} />
            )}
          </fieldset>
        )}
      </main>

      <footer className="mx-auto max-w-[1600px] px-4 pb-6 text-xs text-slate-400">
        Reference demo. The organisation, every asset, site name, engineer and figure is invented. There is no login:
        every connected browser tab sees and can change the same portfolio.
      </footer>
    </div>
  );
}
