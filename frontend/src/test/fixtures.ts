import { vi } from 'vitest';
import type { Asset, Kpis, PipelineBoard, PortfolioSnapshot } from '../types/portfolio';

const STAGES = {
  BUILD_TO_SUIT: ['Engineering Design', 'Planning & Grid Permits', 'Civil Execution', 'Operational Handover'],
  LAND_ACQUISITION: ['Site Scouting', 'Technical Due Diligence', 'Commercial Negotiation', 'Title Closed'],
} as const;

const code = (name: string) => name.toUpperCase().replace(/[^A-Z]+/g, '_');
const label = (index: number, name: string) => `0${index + 1}. ${name}`;

export function makeAsset(overrides: Partial<Asset> = {}): Asset {
  const pipeline = (overrides.pipeline ?? 'BUILD_TO_SUIT') as keyof typeof STAGES;
  const index = overrides.stage_index ?? 1;
  const names = STAGES[pipeline];
  return {
    asset_id: 'AST-406',
    name: 'Thames Corridor Intermodal Yard',
    pipeline,
    stage: code(names[index]),
    stage_index: index,
    stage_label: label(index, names[index]),
    region: 'Thames Estuary',
    area_sqm: 74000,
    capital_value_gbp: '88000000.00',
    lead_engineer: 'Dev Ramaswamy-Clarke',
    gis_coords: { lat: 51.5, lon: 0.4 },
    grid_capacity_mva: 25,
    permits_verified: false,
    risk_level: 'HIGH',
    document_checklist: names.map((name, i) => ({ document: `${name} record`, stage_label: label(i, name), received: i <= index })),
    audit: [{ at: '2026-01-16T08:00:00Z', action: 'CREATED', detail: 'Seed portfolio' }],
    deleted_at: null,
    is_deleted: false,
    retention_days_left: null,
    purge_at: null,
    ...overrides,
  };
}

export const LAND_ASSET = makeAsset({
  asset_id: 'AST-401',
  name: 'Tees Valley Modular Logistics Hub Plot',
  pipeline: 'LAND_ACQUISITION',
  stage_index: 0,
  region: 'Tees Valley',
  capital_value_gbp: '14250000.00',
  gis_coords: { lat: 54.6, lon: -1.2 },
  permits_verified: true,
  risk_level: 'MEDIUM',
});

export const TRASHED = makeAsset({
  asset_id: 'AST-407',
  name: 'Central Scotland Battery Assembly Hall',
  stage_index: 2,
  capital_value_gbp: '134000000.00',
  deleted_at: '2026-03-02T09:30:00Z',
  is_deleted: true,
  retention_days_left: 24,
  purge_at: '2026-04-01T09:30:00Z',
  audit: [
    { at: '2026-01-16T08:00:00Z', action: 'CREATED', detail: 'Seed portfolio' },
    { at: '2026-03-02T09:30:00Z', action: 'DELETED', detail: 'Moved to the trash bin from 03. Civil Execution' },
  ],
});

function board(pipeline: keyof typeof STAGES, labelText: string, short: string, assets: Asset[]): PipelineBoard {
  return {
    pipeline,
    label: labelText,
    short_label: short,
    stages: STAGES[pipeline].map((name, i) => ({ code: code(name), label: label(i, name) })),
    assets: assets.filter((asset) => asset.pipeline === pipeline),
  };
}

export function makeKpis(overrides: Partial<Kpis> = {}): Kpis {
  return {
    active_assets: 2,
    trash_assets: 0,
    total_capital_value_gbp: '102250000.00',
    total_area_sqm: 259000,
    total_grid_capacity_mva: 37,
    permits_verified: 1,
    capital_by_pipeline: [
      { pipeline: 'LAND_ACQUISITION', label: 'Industrial Land', asset_count: 1, capital_value_gbp: '14250000.00' },
      { pipeline: 'BUILD_TO_SUIT', label: 'Build-to-Suit', asset_count: 1, capital_value_gbp: '88000000.00' },
    ],
    funnel: [1, 2, 3, 4].map((position) => ({
      position,
      asset_count: position <= 2 ? 1 : 0,
      capital_value_gbp: position === 1 ? '14250000.00' : position === 2 ? '88000000.00' : '0.00',
      by_pipeline: {},
    })),
    risk_distribution: [
      { risk_level: 'LOW', asset_count: 0, capital_value_gbp: '0.00' },
      { risk_level: 'MEDIUM', asset_count: 1, capital_value_gbp: '14250000.00' },
      { risk_level: 'HIGH', asset_count: 1, capital_value_gbp: '88000000.00' },
    ],
    ...overrides,
  };
}

interface SnapshotOptions {
  sequence?: number;
  assets?: Asset[];
  trash?: Asset[];
}

export function makeSnapshot({ sequence = 0, assets = [LAND_ASSET, makeAsset()], trash = [] }: SnapshotOptions = {}): PortfolioSnapshot {
  return {
    sequence,
    generated_at: '2026-03-02T08:00:00Z',
    organisation: 'Meridian Capital Assets & Infrastructure Sites — UK Operations',
    retention_days: 30,
    pipelines: [
      board('LAND_ACQUISITION', 'Industrial Land & Brownfield Sites', 'Industrial Land', assets),
      board('BUILD_TO_SUIT', 'Custom Industrial & Logistics Facilities', 'Build-to-Suit', assets),
    ],
    trash,
    kpis: makeKpis({ active_assets: assets.length, trash_assets: trash.length }),
    activity: [],
  };
}

/** Replaces `fetch` with a stub answering every call with `body` and `status`. */
export function stubFetch(body: unknown = { sequence: 1 }, status = 200) {
  const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => (typeof body === 'string' ? body : JSON.stringify(body)),
  }));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

/** `[method, path]` of every call made through a `stubFetch` mock. */
export function calls(fetchMock: ReturnType<typeof stubFetch>): [string, string][] {
  return fetchMock.mock.calls.map(([url, init]) => [init?.method ?? 'GET', url]);
}
