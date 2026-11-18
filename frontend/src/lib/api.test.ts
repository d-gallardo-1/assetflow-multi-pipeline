import { afterEach, describe, expect, it, vi } from 'vitest';
import { calls, stubFetch } from '../test/fixtures';
import { api } from './api';

afterEach(() => vi.unstubAllGlobals());

describe('api commands', () => {
  it('uses the method and path of each command', async () => {
    const fetchMock = stubFetch();

    await api.moveStage('AST-401', 'TITLE_CLOSED');
    await api.softDelete('AST-401');
    await api.restore('AST-401');
    await api.purge('AST-401');
    await api.reset();

    expect(calls(fetchMock)).toEqual([
      ['PATCH', '/api/v1/assets/AST-401/stage'],
      ['DELETE', '/api/v1/assets/AST-401'],
      ['POST', '/api/v1/trash/AST-401/restore'],
      ['DELETE', '/api/v1/trash/AST-401/purge'],
      ['POST', '/api/v1/assets/reset'],
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ stage: 'TITLE_CLOSED' });
    expect(fetchMock.mock.calls[1][1]?.body).toBeUndefined();
  });

  it('sends CSV as the raw body and returns the import report', async () => {
    const report = { total_rows: 1, imported: ['AST-601'], rejected_rows: 0, errors: [] };
    const fetchMock = stubFetch(report);

    await expect(api.importCsv('asset_id,name\nAST-601,Plot')).resolves.toEqual(report);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/v1/assets/import-csv');
    expect(init?.body).toBe('asset_id,name\nAST-601,Plot');
    expect((init?.headers as Record<string, string>)['Content-Type']).toBe('text/csv; charset=utf-8');
  });

  it('reads the sample batch as text and keeps downloads on the same origin', async () => {
    stubFetch('asset_id,name\nAST-501,Plot');

    await expect(api.sampleCsv()).resolves.toBe('asset_id,name\nAST-501,Plot');
    expect(api.sampleCsvUrl).toBe('/api/v1/assets/sample-csv');
    expect(api.exportXlsxUrl).toBe('/api/v1/assets/export-xlsx');
  });

  it('reports a refusal in the words of the server', async () => {
    stubFetch({ detail: 'AST-412 is in the trash bin; restore it before moving it.' }, 409);

    await expect(api.moveStage('AST-412', 'UNIT_AVAILABLE')).rejects.toThrow(
      'AST-412 is in the trash bin; restore it before moving it.',
    );
  });

  it('falls back to the method, path and status when the body explains nothing', async () => {
    // Request validation errors carry a list in `detail`, not a sentence.
    stubFetch({ detail: [{ msg: 'String should match pattern' }] }, 422);

    await expect(api.softDelete('nope')).rejects.toThrow('DELETE /assets/nope failed with HTTP 422');
  });
});
