import { afterEach, describe, expect, it, vi } from 'vitest';
import { calls, stubFetch } from '../test/fixtures';
import { api } from './api';
import { formatArea, formatCoords, formatGbp, formatUtc, percentOf } from './format';

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

describe('format', () => {
  it('formats decimal-string money in pounds, in full and compact', () => {
    expect(formatGbp('62500000.00')).toBe('£62,500,000');
    expect(formatGbp('62500000.00', true)).toBe('£62.5M');
    expect(formatGbp('180000.00', true)).toBe('£180K');
    expect(formatGbp('not money')).toBe('£ ?');
  });

  it('formats area, rounded coordinates and labelled UTC time', () => {
    expect(formatArea(185000)).toBe('185,000 sqm');
    expect(formatCoords({ lat: 54.6, lon: -1.2 })).toBe('54.6°N 1.2°W');
    expect(formatCoords({ lat: -33.86, lon: 151.21 })).toBe('33.9°S 151.2°E');
    expect(formatUtc('2026-03-02T10:30:00+01:00')).toBe('2026-03-02 09:30 UTC');
    expect(formatUtc(null)).toBe('unknown time');
  });

  it('computes a share safely when the total is zero', () => {
    expect(percentOf(1, 4)).toBe(25);
    expect(percentOf(1, 3)).toBe(33.3);
    expect(percentOf(5, 0)).toBe(0);
  });
});
