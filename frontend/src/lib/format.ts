const GBP = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 });
const NUMBER = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 });

// Compact amounts are built here instead of with Intl's compact notation, whose
// suffix depends on the ICU data of the runtime: the same code printed "£88M"
// on one Node release and "£88m" on another and in the browser.
const UNITS: [number, string][] = [
  [1e9, 'B'],
  [1e6, 'M'],
  [1e3, 'K'],
];

function compactGbp(amount: number): string {
  for (const [index, [size, suffix]] of UNITS.entries()) {
    // A unit is used from the point where the unit below would round up to
    // 1,000 of its own: 999,960 is "£1M", not "£1000K", and 950 stays "£950".
    const below = UNITS[index + 1]?.[0] ?? 10;
    if (amount >= size - below * 0.05) {
      return `£${NUMBER.format(Math.round((amount / size) * 10) / 10)}${suffix}`;
    }
  }
  return GBP.format(amount);
}

/**
 * Money arrives as a decimal string. It is converted to a number only here, to
 * be shown: the frontend never adds amounts up, the backend does.
 */
export function formatGbp(value: string, compact = false): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return '£ ?';
  return compact ? compactGbp(amount) : GBP.format(amount);
}

export const formatNumber = (value: number): string => NUMBER.format(value);

export const formatArea = (sqm: number): string => `${NUMBER.format(sqm)} sqm`;

/** Rounded to one decimal: the demo never shows a position precise enough to find a site. */
export function formatCoords(coords: { lat: number; lon: number }): string {
  const part = (value: number, positive: string, negative: string) =>
    `${Math.abs(value).toFixed(1)}°${value >= 0 ? positive : negative}`;
  return `${part(coords.lat, 'N', 'S')} ${part(coords.lon, 'E', 'W')}`;
}

/** Always UTC and always labelled, so two sites reading one audit trail agree. */
export function formatUtc(iso: string | null): string {
  const date = new Date(iso ?? '');
  if (Number.isNaN(date.getTime())) return 'unknown time';
  return `${date.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
}

/** Share of `value` in `total` as a 0-100 number, safe when the total is zero. */
export function percentOf(value: number, total: number): number {
  return total > 0 ? Math.round((value / total) * 1000) / 10 : 0;
}
