import { Download, FileUp, PlayCircle, RotateCcw } from 'lucide-react';
import { useRef, useState, type ChangeEvent } from 'react';
import { MAX_CSV_BYTES, MAX_CSV_ROWS, api } from '../../lib/api';
import type { ImportReport } from '../../types/portfolio';
import { ErrorNote } from '../shared/ErrorNote';
import { ValidationLog, type ImportRun } from './ValidationLog';

const COLUMNS =
  'asset_id, name, pipeline, stage, region, area_sqm, capital_value_gbp, lead_engineer, lat, lon, grid_capacity_mva, permits_verified, risk_level';

/** Bulk CSV ingestion: one-click sample batch, upload, paste, and the validation log. */
export function IngestView() {
  const [runs, setRuns] = useState<ImportRun[]>([]);
  const [busy, setBusy] = useState(false);
  const [pasted, setPasted] = useState('');
  const [resetError, setResetError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const record = (source: string, report: ImportReport | null, failure: string | null) =>
    setRuns((current) => [
      { id: current.length + 1, source, at: new Date().toLocaleTimeString('en-GB', { hour12: false }), report, failure },
      ...current,
    ]);

  /** Runs one import and logs its outcome; a failure of any kind becomes a log entry. */
  const attempt = async (source: string, load: () => Promise<string | Blob>) => {
    setBusy(true);
    try {
      record(source, await api.importCsv(await load()), null);
    } catch (cause) {
      record(source, null, cause instanceof Error ? cause.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  };

  const onFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    // Cleared so that choosing the same file again, after fixing it, fires a change.
    event.target.value = '';
    if (!file) return;
    if (file.size > MAX_CSV_BYTES) {
      record(file.name, null, `The file is larger than the ${MAX_CSV_BYTES / 1024} KB limit.`);
      return;
    }
    void attempt(file.name, async () => file);
  };

  const reset = async () => {
    setBusy(true);
    try {
      await api.reset();
      setRuns([]);
      setResetError(null);
    } catch (cause) {
      setResetError(`Reset failed. ${cause instanceof Error ? cause.message : 'Request failed'}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="space-y-4" aria-label="Bulk CSV ingestion and schema validator">
      <div className="panel space-y-3 p-4">
        <h2 className="panel-title">Bulk CSV ingestion</h2>
        <p className="text-sm text-slate-300">
          Valid rows are imported; each invalid row is listed below with its row number, column and reason. An asset
          id that is repeated in the file, already active or in the trash bin is rejected, never overwritten. Limits:
          {` ${MAX_CSV_BYTES / 1024} KB`} and {MAX_CSV_ROWS} data rows, UTF-8.
        </p>
        <p className="font-mono text-xs text-slate-400">Columns: {COLUMNS}</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-primary"
            disabled={busy}
            onClick={() => void attempt('Built-in sample batch', api.sampleCsv)}
          >
            <PlayCircle aria-hidden="true" className="h-4 w-4" />
            Simulate Bulk CSV Import (5 Assets)
          </button>
          <button type="button" className="btn" disabled={busy} onClick={() => input.current?.click()}>
            <FileUp aria-hidden="true" className="h-4 w-4" />
            Upload CSV file
          </button>
          <input ref={input} type="file" accept=".csv,text/csv" className="sr-only" aria-label="CSV file" onChange={onFile} />
          <a className="btn" href={api.sampleCsvUrl} download>
            <Download aria-hidden="true" className="h-4 w-4" />
            Download sample CSV
          </a>
          <button type="button" className="btn ml-auto" disabled={busy} onClick={() => void reset()}>
            <RotateCcw aria-hidden="true" className="h-4 w-4" />
            Reset demo data
          </button>
        </div>

        <ErrorNote message={resetError} />

        <label className="block text-xs text-slate-400">
          Or paste CSV text, header row first
          <textarea
            className="field mt-1 h-32 font-mono text-xs"
            value={pasted}
            spellCheck={false}
            onChange={(event) => setPasted(event.target.value)}
            placeholder={COLUMNS.replace(/, /g, ',')}
          />
        </label>
        <button
          type="button"
          className="btn-primary"
          disabled={busy || !pasted.trim()}
          onClick={() => void attempt('Pasted text', async () => pasted)}
        >
          Validate and import pasted CSV
        </button>
      </div>

      <div className="panel space-y-3 p-4" aria-live="polite">
        <h2 className="panel-title">Validation log</h2>
        <ValidationLog runs={runs} />
      </div>
    </section>
  );
}
