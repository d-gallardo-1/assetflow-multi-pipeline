import type { ReactNode } from 'react';

export interface BarRow {
  key: string;
  label: ReactNode;
  /** Shown as text next to the bar: the bar is never the only carrier of the figure. */
  value: string;
  /** 0 to 100. */
  percent: number;
}

const FILLS = { link: 'fill-link', nominal: 'fill-nominal', warn: 'fill-warn', critical: 'fill-critical' } as const;

interface Props {
  caption: string;
  rows: BarRow[];
  tone?: keyof typeof FILLS | ((row: BarRow) => keyof typeof FILLS);
}

/**
 * Horizontal bars drawn as SVG. Widths are SVG attributes, not inline styles,
 * so they render under a Content Security Policy without `unsafe-inline`.
 */
export function BarList({ caption, rows, tone = 'link' }: Props) {
  return (
    <ul aria-label={caption} className="space-y-2">
      {rows.map((row) => {
        const fill = FILLS[typeof tone === 'function' ? tone(row) : tone];
        return (
          <li key={row.key} className="text-sm">
            <p className="flex items-baseline justify-between gap-3">
              <span className="text-slate-200">{row.label}</span>
              <span className="font-mono text-slate-100">{row.value}</span>
            </p>
            <svg aria-hidden="true" viewBox="0 0 100 4" preserveAspectRatio="none" className="mt-1 h-2 w-full rounded-sm">
              <rect width="100" height="4" className="fill-edge" />
              <rect width={Math.max(0, Math.min(100, row.percent))} height="4" className={fill} />
            </svg>
          </li>
        );
      })}
    </ul>
  );
}
