const GBP = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 });
const GBP_COMPACT = new Intl.NumberFormat('en-GB', {
  style: 'currency',
  currency: 'GBP',
  notation: 'compact',
  // Without this, a currency keeps a trailing zero: "£88.0M".
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
});
const NUMBER = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 });

/**
 * Money arrives as a decimal string. It is converted to a number only here, to
 * be shown: the frontend never adds amounts up, the backend does.
 */
export function formatGbp(value: string, compact = false): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return '£ ?';
  return (compact ? GBP_COMPACT : GBP).format(amount);
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
