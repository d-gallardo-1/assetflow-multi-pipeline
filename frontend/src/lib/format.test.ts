import { describe, expect, it } from 'vitest';
import { formatArea, formatCoords, formatGbp, formatUtc, percentOf } from './format';

describe('format', () => {
  it('formats decimal-string money in pounds, in full and compact', () => {
    expect(formatGbp('62500000.00')).toBe('£62,500,000');
    expect(formatGbp('62500000.00', true)).toBe('£62.5M');
    expect(formatGbp('180000.00', true)).toBe('£180K');
    expect(formatGbp('2400000000.00', true)).toBe('£2.4B');
    expect(formatGbp('999960.00', true)).toBe('£1M');
    expect(formatGbp('950.00', true)).toBe('£950');
    expect(formatGbp('0.00', true)).toBe('£0');
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
