import {
  AlertTriangle, BadgeCheck, CircleCheck, Clock, Hourglass, MapPin, OctagonAlert, Radio, RefreshCw, WifiOff,
  type LucideIcon,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { formatCoords } from '../../lib/format';
import type { RiskLevel, StreamStatus } from '../../types/portfolio';

// Tailwind only generates classes it can see as complete strings, so every
// tone lists its classes explicitly instead of building them dynamically.
const TONES = {
  nominal: 'text-nominal border-nominal/50 bg-nominal/10',
  warn: 'text-warn border-warn/50 bg-warn/10',
  critical: 'text-red-400 border-critical/60 bg-critical/10',
  link: 'text-link border-link/50 bg-link/10',
  neutral: 'text-slate-300 border-edge bg-obsidian',
} as const;

type Tone = keyof typeof TONES;

interface BadgeProps {
  tone: Tone;
  icon: LucideIcon;
  label?: string;
  children: ReactNode;
}

/** Colour, icon and text together: no status depends on colour alone. */
function Badge({ tone, icon: Icon, label, children }: BadgeProps) {
  return (
    <span
      aria-label={label}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded border px-1.5 py-0.5 font-mono text-[11px] font-semibold tracking-wide ${TONES[tone]}`}
    >
      <Icon aria-hidden="true" className="h-3 w-3 shrink-0" />
      {children}
    </span>
  );
}

const RISK: Record<RiskLevel, { tone: 'nominal' | 'warn' | 'critical'; icon: LucideIcon }> = {
  LOW: { tone: 'nominal', icon: CircleCheck },
  MEDIUM: { tone: 'warn', icon: AlertTriangle },
  HIGH: { tone: 'critical', icon: OctagonAlert },
};

/** The tone of a risk level, for charts that must agree with the badge. */
export const riskTone = (level: RiskLevel) => RISK[level].tone;

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <Badge {...RISK[level]} label={`Risk: ${level}`}>
      {level} RISK
    </Badge>
  );
}

export function PermitBadge({ verified }: { verified: boolean }) {
  return verified ? (
    <Badge tone="nominal" icon={BadgeCheck}>PERMITS VERIFIED</Badge>
  ) : (
    <Badge tone="warn" icon={Hourglass}>PERMITS PENDING</Badge>
  );
}

export function CoordsBadge({ coords }: { coords: { lat: number; lon: number } }) {
  return (
    <Badge tone="neutral" icon={MapPin} label={`Approximate position ${formatCoords(coords)}`}>
      {formatCoords(coords)}
    </Badge>
  );
}

/** Amber in the last week of retention; the number of days is always written out. */
export function RetentionBadge({ daysLeft }: { daysLeft: number | null }) {
  if (daysLeft === null) {
    return (
      <Badge tone="neutral" icon={Clock}>
        RETENTION UNKNOWN
      </Badge>
    );
  }
  const days = daysLeft;
  return (
    <Badge tone={days <= 7 ? 'warn' : 'neutral'} icon={Clock}>
      {days} {days === 1 ? 'DAY' : 'DAYS'} LEFT
    </Badge>
  );
}

const STREAM: Record<StreamStatus, { tone: Tone; icon: LucideIcon; label: string }> = {
  CONNECTED: { tone: 'link', icon: Radio, label: 'LIVE' },
  RECONNECTING: { tone: 'warn', icon: RefreshCw, label: 'RECONNECTING' },
  DISCONNECTED: { tone: 'critical', icon: WifiOff, label: 'DISCONNECTED' },
};

export function StreamBadge({ status }: { status: StreamStatus }) {
  const { tone, icon, label } = STREAM[status];
  return (
    <Badge tone={tone} icon={icon} label={`Live stream: ${label}`}>
      {label}
    </Badge>
  );
}
