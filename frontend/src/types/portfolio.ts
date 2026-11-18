// Mirrors backend/app/models.py. The backend is the source of truth.

export type Pipeline = 'LAND_ACQUISITION' | 'BUILD_TO_SUIT' | 'MULTI_TENANT_PARKS' | 'ADVISORY_VALUATION';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';
export type StreamStatus = 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED';
export type ViewId = 'board' | 'analytics' | 'ingest' | 'trash';
export type AuditAction = 'CREATED' | 'MOVED' | 'DELETED' | 'RESTORED' | 'PURGED';

export interface AuditEntry {
  at: string;
  action: AuditAction;
  detail: string;
}

export interface ChecklistItem {
  document: string;
  stage_label: string;
  received: boolean;
}

export interface Asset {
  asset_id: string;
  name: string;
  pipeline: Pipeline;
  stage: string;
  stage_index: number;
  stage_label: string;
  region: string;
  area_sqm: number;
  /** Money travels as a decimal string, for example "62500000.00". */
  capital_value_gbp: string;
  lead_engineer: string;
  gis_coords: { lat: number; lon: number };
  grid_capacity_mva: number;
  permits_verified: boolean;
  risk_level: RiskLevel;
  document_checklist: ChecklistItem[];
  audit: AuditEntry[];
  deleted_at: string | null;
  is_deleted: boolean;
  retention_days_left: number | null;
  purge_at: string | null;
}

export interface StageInfo {
  code: string;
  label: string;
}

export interface PipelineBoard {
  pipeline: Pipeline;
  label: string;
  short_label: string;
  stages: StageInfo[];
  assets: Asset[];
}

export interface PipelineTotal {
  pipeline: Pipeline;
  label: string;
  asset_count: number;
  capital_value_gbp: string;
}

export interface FunnelStep {
  position: number;
  asset_count: number;
  capital_value_gbp: string;
  by_pipeline: Record<string, number>;
}

export interface RiskTotal {
  risk_level: RiskLevel;
  asset_count: number;
  capital_value_gbp: string;
}

export interface Kpis {
  active_assets: number;
  trash_assets: number;
  total_capital_value_gbp: string;
  total_area_sqm: number;
  total_grid_capacity_mva: number;
  permits_verified: number;
  capital_by_pipeline: PipelineTotal[];
  funnel: FunnelStep[];
  risk_distribution: RiskTotal[];
}

export interface ActivityEntry {
  asset_id: string;
  name: string;
  entry: AuditEntry;
}

export interface PortfolioSnapshot {
  sequence: number;
  generated_at: string;
  organisation: string;
  retention_days: number;
  pipelines: PipelineBoard[];
  trash: Asset[];
  kpis: Kpis;
  activity: ActivityEntry[];
}

export interface RowError {
  row: number;
  column: string;
  reason: string;
  value: string;
}

export interface ImportReport {
  total_rows: number;
  imported: string[];
  rejected_rows: number;
  errors: RowError[];
}
