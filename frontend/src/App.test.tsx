import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { FakeEventSource } from './test/fakeEventSource';
import { LAND_ASSET, TRASHED, makeAsset, makeSnapshot } from './test/fixtures';

beforeEach(() => {
  FakeEventSource.reset();
  vi.stubGlobal('EventSource', FakeEventSource);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const emit = (type: string, data: unknown) => act(() => FakeEventSource.latest.emit(type, data));
const view = (name: RegExp) => screen.getByRole('button', { name }) as HTMLButtonElement;

function giveUpOnTheStream() {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    act(() => FakeEventSource.latest.fail(true));
    act(() => vi.advanceTimersByTime(3000));
  }
}

describe('App', () => {
  it('waits for the first snapshot, then shows the organisation, KPIs and the board', () => {
    render(<App />);
    expect(screen.getByRole('status').textContent).toContain('Waiting for the first portfolio snapshot');

    emit('snapshot', makeSnapshot());

    expect(screen.getByText('Meridian Capital Assets & Infrastructure Sites — UK Operations')).toBeTruthy();
    expect(screen.getByText('Capital under management').nextSibling?.textContent).toBe('£102.3M');
    expect(screen.getByLabelText('Live stream: LIVE')).toBeTruthy();
    expect(screen.getByText('AST-401')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('follows a delete and a restore made in another tab', () => {
    render(<App />);
    emit('snapshot', makeSnapshot({ assets: [LAND_ASSET, makeAsset({ asset_id: 'AST-407', stage_index: 2 })] }));
    fireEvent.click(screen.getByRole('tab', { name: /Build-to-Suit/ }));
    expect(screen.getByText('AST-407')).toBeTruthy();

    emit('update', makeSnapshot({ sequence: 1, assets: [LAND_ASSET], trash: [TRASHED] }));

    expect(screen.queryByText('AST-407')).toBeNull();
    fireEvent.click(view(/Trash Bin & Audit Vault \(1\)/));
    expect(screen.getByRole('article', { name: 'AST-407 in the trash bin' })).toBeTruthy();

    emit('update', makeSnapshot({ sequence: 2 }));
    expect(screen.getByText('The trash bin is empty.')).toBeTruthy();
  });

  it('offers the four views', () => {
    render(<App />);
    emit('snapshot', makeSnapshot());

    fireEvent.click(view(/Portfolio Analytics/));
    expect(screen.getByRole('region', { name: 'Executive portfolio analytics' })).toBeTruthy();
    fireEvent.click(view(/CSV Ingestion/));
    expect(screen.getByRole('button', { name: 'Simulate Bulk CSV Import (5 Assets)' })).toBeTruthy();
    fireEvent.click(view(/Trash Bin/));
    expect(screen.getByRole('region', { name: 'Soft-delete trash bin and audit vault' })).toBeTruthy();
    fireEvent.click(view(/Kanban Board/));
    expect(screen.getByRole('region', { name: 'Multi-pipeline Kanban board' })).toBeTruthy();
  });

  it('warns and disables the controls once the stream is given up on, but not navigation', () => {
    vi.useFakeTimers();
    try {
      render(<App />);
      emit('snapshot', makeSnapshot());

      giveUpOnTheStream();

      expect(screen.getByRole('alert').textContent).toContain('controls are disabled');
      expect(view(/Move AST-401 to the trash bin/).matches(':disabled')).toBe(true);
      expect(view(/Portfolio Analytics/).matches(':disabled')).toBe(false);
    } finally {
      vi.useRealTimers();
    }
  });

  it('explains the situation when no snapshot has ever arrived', () => {
    vi.useFakeTimers();
    try {
      render(<App />);
      giveUpOnTheStream();

      expect(screen.getByRole('status').textContent).toContain('Cannot reach the backend');
      expect(screen.queryByRole('tab')).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });
});
