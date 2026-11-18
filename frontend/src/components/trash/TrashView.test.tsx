import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { TRASHED, calls, makeSnapshot, stubFetch } from '../../test/fixtures';
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

  it('keeps the confirmation of a second asset open when the first purge finishes', async () => {
    stubFetch();
    const other = { ...TRASHED, asset_id: 'AST-412', name: 'Humber Port-Side Storage Terrace' };
    renderTrash([TRASHED, other]);

    fireEvent.click(button('Permanent purge of AST-407'));
    fireEvent.click(button('Confirm purge of AST-407'));
    fireEvent.click(button('Permanent purge of AST-412'));

    await waitFor(() => expect(button('Permanent purge of AST-407')).toBeTruthy());
    expect(button('Confirm purge of AST-412')).toBeTruthy();
  });

  it('says so when the retention of a trashed asset is unknown', () => {
    renderTrash([{ ...TRASHED, retention_days_left: null }]);

    expect(screen.getByText('RETENTION UNKNOWN')).toBeTruthy();
  });

  it('reports a refused restore', async () => {
    stubFetch({ detail: 'AST-407 does not exist.' }, 404);
    renderTrash();

    fireEvent.click(button(/Restore AST-407/));

    expect((await screen.findByRole('alert')).textContent).toBe('AST-407 does not exist.');
  });
});
