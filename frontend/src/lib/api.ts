import type { ImportReport } from '../types/portfolio';

// Same-origin API: Nginx (Docker) or the Vite dev server proxies /api to the backend.
export const API_BASE = '/api/v1';

/** Mirrors MAX_CSV_BYTES in backend/app/exchange/csv_import.py. */
export const MAX_CSV_BYTES = 256 * 1024;
/** Mirrors MAX_CSV_ROWS in the same backend module. */
export const MAX_CSV_ROWS = 500;

/** Uses the server's own explanation when it sends one, so refusals are readable. */
async function errorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') return body.detail;
  } catch {
    /* not JSON: fall through */
  }
  return fallback;
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const fallback = `${init?.method ?? 'GET'} ${path} failed with HTTP ${response.status}`;
    throw new Error(await errorMessage(response, fallback));
  }
  return response;
}

const command = (method: string, path: string, body?: unknown) =>
  send(path, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

const id = (assetId: string) => encodeURIComponent(assetId);

export const api = {
  moveStage: (assetId: string, stage: string) => command('PATCH', `/assets/${id(assetId)}/stage`, { stage }),
  softDelete: (assetId: string) => command('DELETE', `/assets/${id(assetId)}`),
  restore: (assetId: string) => command('POST', `/trash/${id(assetId)}/restore`),
  purge: (assetId: string) => command('DELETE', `/trash/${id(assetId)}/purge`),
  reset: () => command('POST', '/assets/reset'),
  /** The CSV travels as the raw request body, whether it was uploaded or pasted. */
  importCsv: async (csv: string | Blob): Promise<ImportReport> => {
    const response = await send('/assets/import-csv', {
      method: 'POST',
      headers: { 'Content-Type': 'text/csv; charset=utf-8' },
      body: csv,
    });
    return (await response.json()) as ImportReport;
  },
  sampleCsv: async (): Promise<string> => (await send('/assets/sample-csv')).text(),
  sampleCsvUrl: `${API_BASE}/assets/sample-csv`,
  exportXlsxUrl: `${API_BASE}/assets/export-xlsx`,
};
