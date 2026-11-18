import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { LAND_ASSET, calls, makeAsset, makeSnapshot, stubFetch } from '../../test/fixtures';
import { KanbanBoard } from './KanbanBoard';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const renderBoard = (snapshot = makeSnapshot()) =>
  render(<KanbanBoard pipelines={snapshot.pipelines} retentionDays={snapshot.retention_days} />);
const tab = (name: RegExp) => screen.getByRole('tab', { name });
const column = (name: string) => screen.getByRole('region', { name });
const button = (name: string) => screen.getByRole('button', { name }) as HTMLButtonElement;

describe('KanbanBoard', () => {
  it('opens on the first pipeline with its four stage columns', () => {
    renderBoard();

    expect(tab(/Industrial Land/).getAttribute('aria-selected')).toBe('true');
    for (const stage of ['01. Site Scouting', '02. Technical Due Diligence', '03. Commercial Negotiation', '04. Title Closed']) {
      expect(column(stage)).toBeTruthy();
    }
    expect(within(column('01. Site Scouting')).getByText('AST-401')).toBeTruthy();
    expect(within(column('04. Title Closed')).getByText('No assets at this stage')).toBeTruthy();
    expect(screen.queryByText('AST-406')).toBeNull();
  });

  it('switches pipeline with the tabs', () => {
    renderBoard();

    fireEvent.click(tab(/Build-to-Suit/));

    expect(tab(/Build-to-Suit/).getAttribute('aria-selected')).toBe('true');
    expect(within(column('02. Planning & Grid Permits')).getByText('AST-406')).toBeTruthy();
    expect(screen.queryByText('AST-401')).toBeNull();
  });

  it('shows the figures and status badges of a card as text', () => {
    renderBoard();
    fireEvent.click(tab(/Build-to-Suit/));

    const card = screen.getByRole('article', { name: 'AST-406 Thames Corridor Intermodal Yard' });
    for (const text of ['£88M', '74,000 sqm', '25 MVA', '51.5°N 0.4°E', 'PERMITS PENDING', 'HIGH RISK', 'Documents on file: 2 of 4']) {
      expect(card.textContent).toContain(text);
    }
    expect(screen.queryByText('PERMITS VERIFIED')).toBeNull();
  });

  it('moves an asset to the next and to the previous stage with labelled buttons', async () => {
    const fetchMock = stubFetch();
    renderBoard();
    fireEvent.click(tab(/Build-to-Suit/));

    fireEvent.click(button('Move AST-406 forward to 03. Civil Execution'));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    fireEvent.click(button('Move AST-406 back to 01. Engineering Design'));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    expect(calls(fetchMock)).toEqual([
      ['PATCH', '/api/v1/assets/AST-406/stage'],
      ['PATCH', '/api/v1/assets/AST-406/stage'],
    ]);
    const stages = fetchMock.mock.calls.map(([, init]) => JSON.parse(String(init?.body)).stage);
    expect(stages).toEqual(['CIVIL_EXECUTION', 'ENGINEERING_DESIGN']);
  });

  it('disables the move that does not exist at either end of the pipeline', () => {
    const last = makeAsset({ asset_id: 'AST-408', stage_index: 3 });
    renderBoard(makeSnapshot({ assets: [LAND_ASSET, last] }));

    expect(button('AST-401 is at the first stage').disabled).toBe(true);
    expect(button('Move AST-401 forward to 02. Technical Due Diligence').disabled).toBe(false);
    fireEvent.click(tab(/Build-to-Suit/));
    expect(button('AST-408 is at the last stage').disabled).toBe(true);
  });

  it('soft-deletes an asset from its card', async () => {
    const fetchMock = stubFetch();
    renderBoard();

    fireEvent.click(button('Move AST-401 to the trash bin'));

    await waitFor(() => expect(calls(fetchMock)).toEqual([['DELETE', '/api/v1/assets/AST-401']]));
  });

  it('shows the reason when the server refuses a move', async () => {
    stubFetch({ detail: 'AST-401 is in the trash bin; restore it before moving it.' }, 409);
    renderBoard();

    fireEvent.click(button('Move AST-401 forward to 02. Technical Due Diligence'));

    expect((await screen.findByRole('alert')).textContent).toBe('AST-401 is in the trash bin; restore it before moving it.');
  });

  it('follows a new snapshot: the card changes column and a deleted card leaves', () => {
    const { rerender } = renderBoard();
    const moved = makeSnapshot({ assets: [{ ...LAND_ASSET, stage_index: 2 }] });

    rerender(<KanbanBoard pipelines={moved.pipelines} retentionDays={30} />);
    expect(within(column('03. Commercial Negotiation')).getByText('AST-401')).toBeTruthy();

    rerender(<KanbanBoard pipelines={makeSnapshot({ assets: [] }).pipelines} retentionDays={30} />);
    expect(screen.queryByText('AST-401')).toBeNull();
  });
});
