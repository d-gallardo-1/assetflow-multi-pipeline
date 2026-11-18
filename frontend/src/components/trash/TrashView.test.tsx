import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { TRASHED, calls, makeSnapshot, stubFetch } from '../../test/fixtures';
import { AnalyticsView } from '../analytics/AnalyticsView';
import { TrashView } from './TrashView';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderTrash(trash = [TRASHED]) {
  const snapshot = makeSnapshot({ trash });
  return render(<TrashView trash={snapshot.trash} pipelines={snapshot.pipelines} retentionDays={30} />);
}

const button = (name: string | RegExp) => screen.getByRole('button', { name }) as HTMLButtonElement;

describe('TrashView', () => {
  it('says so when it is empty', () => {
    renderTrash([]);

    expect(screen.getByText('The trash bin is empty.')).toBeTruthy();
    expect(screen.queryByRole('article')).toBeNull();
  });

  it('shows when the asset was deleted, how long it stays and where it came from', () => {
    renderTrash();

    const entry = screen.getByRole('article', { name: 'AST-407 in the trash bin' });
    for (const text of [
      'Central Scotland Battery Assembly Hall', '24 DAYS LEFT', 'Build-to-Suit · 03. Civil Execution',
      'Deleted 2026-03-02 09:30 UTC', 'purged automatically 2026-04-01 09:30 UTC',
    ]) {
      expect(entry.textContent).toContain(text);
    }
  });

  it('keeps the audit trail of a deleted asset on view', () => {
    renderTrash();

    const trail = within(screen.getByRole('list', { name: 'Audit trail of AST-407' })).getAllByRole('listitem');
    expect(trail.map((item) => item.textContent)).toEqual([
      '2026-01-16 08:00 UTC CREATED: Seed portfolio',
      '2026-03-02 09:30 UTC DELETED: Moved to the trash bin from 03. Civil Execution',
    ]);
  });

  it('uses the singular for the last day of retention', () => {
    renderTrash([{ ...TRASHED, retention_days_left: 1 }]);

    expect(screen.getByText('1 DAY LEFT')).toBeTruthy();
  });

  it('restores an asset to its pipeline and stage', async () => {
    const fetchMock = stubFetch();
    renderTrash();

    fireEvent.click(button('Restore AST-407 to Build-to-Suit, 03. Civil Execution'));

    await waitFor(() => expect(calls(fetchMock)).toEqual([['POST', '/api/v1/trash/AST-407/restore']]));
  });

  it('purges only after an explicit confirmation', async () => {
    const fetchMock = stubFetch();
    renderTrash();

    fireEvent.click(button('Permanent purge of AST-407'));
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toContain('This cannot be undone.');

    fireEvent.click(button('Cancel'));
    expect(screen.queryByRole('alert')).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();

    fireEvent.click(button('Permanent purge of AST-407'));
    fireEvent.click(button('Confirm purge of AST-407'));
    await waitFor(() => expect(calls(fetchMock)).toEqual([['DELETE', '/api/v1/trash/AST-407/purge']]));
  });

  it('reports a refused restore', async () => {
    stubFetch({ detail: 'AST-407 does not exist.' }, 404);
    renderTrash();

    fireEvent.click(button(/Restore AST-407/));

    expect((await screen.findByRole('alert')).textContent).toBe('AST-407 does not exist.');
  });
});

describe('AnalyticsView', () => {
  it('shows capital by pipeline, the funnel, risk and totals as text', () => {
    render(<AnalyticsView kpis={makeSnapshot().kpis} />);

    const rows = (name: string) =>
      within(screen.getByRole('list', { name })).getAllByRole('listitem').map((item) => item.textContent);
    expect(rows('Capital value by pipeline')).toEqual(['Industrial Land (1 asset)£14.3M', 'Build-to-Suit (1 asset)£88M']);
    expect(rows('Funnel across stages')).toEqual([
      'Stage 1 (£14.3M)1 asset', 'Stage 2 (£88M)1 asset', 'Stage 3 (£0)0 assets', 'Stage 4 (£0)0 assets',
    ]);
    expect(rows('Risk distribution')[2]).toBe('HIGH RISK1 asset · £88M');
    const totals = screen.getByRole('region', { name: 'Portfolio totals' }).textContent;
    expect(totals).toContain('259,000 sqm');
    expect(totals).toContain('37 MVA');
    expect(totals).toContain('1 of 2');
    expect(screen.getByText('£102,250,000')).toBeTruthy();
  });

  it('draws each bar in proportion and links the export to the same origin', () => {
    const { container } = render(<AnalyticsView kpis={makeSnapshot().kpis} />);

    const widths = [...container.querySelectorAll('ul[aria-label="Capital value by pipeline"] rect:last-child')].map(
      (bar) => bar.getAttribute('width'),
    );
    expect(widths).toEqual(['13.9', '86.1']);
    expect(screen.getByRole('link', { name: 'Export portfolio (.xlsx)' }).getAttribute('href')).toBe(
      '/api/v1/assets/export-xlsx',
    );
  });
});
