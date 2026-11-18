import { CircleCheck, OctagonAlert, TriangleAlert } from 'lucide-react';
import type { ImportReport } from '../../types/portfolio';

export interface ImportRun {
  id: number;
  source: string;
  /** Local wall-clock time of the run: this log lives in the browser tab only. */
  at: string;
  report: ImportReport | null;
  /** Set when the whole file was refused. */
  failure: string | null;
}

function Summary({ run }: { run: ImportRun }) {
  if (run.failure !== null) {
    return (
      <p className="flex items-start gap-2 text-critical">
        <OctagonAlert aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
        <span>File rejected, nothing imported. {run.failure}</span>
      </p>
    );
  }
  const report = run.report as ImportReport;
  const clean = report.rejected_rows === 0;
  const Icon = clean ? CircleCheck : TriangleAlert;
  return (
    <p className={`flex items-start gap-2 ${clean ? 'text-nominal' : 'text-warn'}`}>
      <Icon aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
      <span>
        {report.imported.length} of {report.total_rows} rows imported
        {report.imported.length > 0 ? ` (${report.imported.join(', ')})` : ''}; {report.rejected_rows} rejected.
      </span>
    </p>
  );
}

/** Newest run first. Each rejected row is located by row number, column and reason. */
export function ValidationLog({ runs }: { runs: ImportRun[] }) {
  if (runs.length === 0) {
    return <p className="text-sm text-slate-400">No import has run in this tab yet.</p>;
  }
  return (
    <ol aria-label="Validation log" className="space-y-3">
      {runs.map((run) => (
        <li key={run.id} className="rounded-md border border-edge bg-obsidian p-3 text-sm">
          <p className="mb-1 font-mono text-xs text-slate-400">
            {run.at} · {run.source}
          </p>
          <Summary run={run} />
          {run.report && run.report.errors.length > 0 && (
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-left text-slate-200">
                <thead className="text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    {['Row', 'Column', 'Value', 'Reason'].map((heading) => (
                      <th key={heading} scope="col" className="px-2 py-1 font-semibold">
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {run.report.errors.map((error, index) => (
                    <tr key={index} className="border-t border-edge/60 align-top">
                      <td className="px-2 py-1 font-mono">{error.row}</td>
                      <td className="px-2 py-1 font-mono">{error.column}</td>
                      <td className="px-2 py-1 font-mono text-slate-400">{error.value || '-'}</td>
                      <td className="px-2 py-1">{error.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
