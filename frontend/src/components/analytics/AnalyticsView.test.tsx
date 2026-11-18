import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { makeSnapshot } from '../../test/fixtures';
import { AnalyticsView } from './AnalyticsView';

afterEach(cleanup);

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
