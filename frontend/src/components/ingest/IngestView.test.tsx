import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MAX_CSV_BYTES } from '../../lib/api';
import { calls, stubFetch } from '../../test/fixtures';
import { IngestView } from './IngestView';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const CLEAN = { total_rows: 5, imported: ['AST-501', 'AST-502', 'AST-503', 'AST-504', 'AST-505'], rejected_rows: 0, errors: [] };
const PARTIAL = {
  total_rows: 3,
  imported: ['AST-601', 'AST-603'],
  rejected_rows: 1,
  errors: [{ row: 3, column: 'risk_level', reason: "Input should be 'LOW', 'MEDIUM' or 'HIGH'", value: 'SEVERE' }],
};

const log = () => screen.getByRole('list', { name: 'Validation log' });
const button = (name: string) => screen.getByRole('button', { name }) as HTMLButtonElement;

describe('IngestView', () => {
  it('starts with an empty log and same-origin sample download', () => {
    render(<IngestView />);

    expect(screen.getByText('No import has run in this tab yet.')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Download sample CSV' }).getAttribute('href')).toBe('/api/v1/assets/sample-csv');
    expect(button('Validate and import pasted CSV').disabled).toBe(true);
  });

  it('runs the one-click demo: fetches the sample batch, imports it and logs the result', async () => {
    const fetchMock = stubFetch(CLEAN);
    render(<IngestView />);

    fireEvent.click(button('Simulate Bulk CSV Import (5 Assets)'));

    await waitFor(() => expect(log().textContent).toContain('5 of 5 rows imported (AST-501, AST-502, AST-503, AST-504, AST-505); 0 rejected.'));
    expect(log().textContent).toContain('Built-in sample batch');
    expect(calls(fetchMock)).toEqual([
      ['GET', '/api/v1/assets/sample-csv'],
      ['POST', '/api/v1/assets/import-csv'],
    ]);
  });

  it('imports pasted text and lists each rejected row with row, column, value and reason', async () => {
    const fetchMock = stubFetch(PARTIAL);
    render(<IngestView />);

    fireEvent.change(screen.getByLabelText(/Or paste CSV text/), { target: { value: 'asset_id,name\nAST-601,Plot' } });
    fireEvent.click(button('Validate and import pasted CSV'));

    await waitFor(() => expect(log().textContent).toContain('2 of 3 rows imported (AST-601, AST-603); 1 rejected.'));
    expect(fetchMock.mock.calls[0][1]?.body).toBe('asset_id,name\nAST-601,Plot');
    const [, row] = within(log()).getAllByRole('row');
    expect(within(row).getAllByRole('cell').map((cell) => cell.textContent)).toEqual([
      '3', 'risk_level', 'SEVERE', "Input should be 'LOW', 'MEDIUM' or 'HIGH'",
    ]);
  });

  it('uploads a chosen file as the request body', async () => {
    const fetchMock = stubFetch(CLEAN);
    render(<IngestView />);
    const file = new File(['asset_id,name'], 'batch.csv', { type: 'text/csv' });

    fireEvent.change(screen.getByLabelText('CSV file'), { target: { files: [file] } });

    await waitFor(() => expect(log().textContent).toContain('batch.csv'));
    expect(fetchMock.mock.calls[0][1]?.body).toBe(file);
  });

  it('logs a file the server rejects as a whole', async () => {
    stubFetch({ detail: 'Header row rejected. Missing column(s): region.' }, 422);
    render(<IngestView />);

    fireEvent.change(screen.getByLabelText(/Or paste CSV text/), { target: { value: 'asset_id\nAST-601' } });
    fireEvent.click(button('Validate and import pasted CSV'));

    await waitFor(() =>
      expect(log().textContent).toContain('File rejected, nothing imported. Header row rejected. Missing column(s): region.'),
    );
  });

  it('refuses an oversized file without sending it', () => {
    const fetchMock = stubFetch();
    render(<IngestView />);

    fireEvent.change(screen.getByLabelText('CSV file'), {
      target: { files: [new File([new Uint8Array(MAX_CSV_BYTES + 1)], 'huge.csv')] },
    });

    expect(log().textContent).toContain('The file is larger than the 256 KB limit.');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('keeps earlier runs in the log, newest first, and clears it on reset', async () => {
    const fetchMock = stubFetch(CLEAN);
    render(<IngestView />);
    fireEvent.click(button('Simulate Bulk CSV Import (5 Assets)'));
    await waitFor(() => expect(within(log()).getAllByRole('listitem')).toHaveLength(1));

    fireEvent.change(screen.getByLabelText(/Or paste CSV text/), { target: { value: 'x' } });
    fireEvent.click(button('Validate and import pasted CSV'));
    await waitFor(() => expect(within(log()).getAllByRole('listitem')).toHaveLength(2));
    expect(within(log()).getAllByRole('listitem')[0].textContent).toContain('Pasted text');

    fireEvent.click(button('Reset demo data'));
    await waitFor(() => expect(screen.getByText('No import has run in this tab yet.')).toBeTruthy());
    expect(calls(fetchMock).slice(-1)).toEqual([['POST', '/api/v1/assets/reset']]);
  });
});
