export type MacroCapabilityStatus = 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE';

export interface Entity {
  id: string;
  ticker: string;
  name: string;
  type?: string;
}

export interface Period {
  id: string;
  quarter: number;
  year: number;
  label?: string;
}

export interface Metric {
  id: string;
  acronym: string;
  label: string;
  topicId: string;
  shortLabel?: string;
  unit?: string;
  direction?: 'higher_is_better' | 'lower_is_better' | 'neutral' | string;
  decimals?: number;
  group?: string;
  groupLabel?: string;
}

export interface TopicPreset {
  id: string;
  label: string;
  metricIds: string[];
}

export interface PeerUniverse {
  id: string;
  label: string;
  entityIds: string[];
  readonly: true;
  description: string;
  executable?: boolean;
}

export interface MacroCapability {
  status: MacroCapabilityStatus;
  minimumContractSatisfied: boolean;
  summary: string;
  details: string;
  executable?: boolean;
}

export interface AnalysisCapabilities {
  /** Identifier for the API capability catalog; it is not a validated data snapshot. */
  snapshotId?: string | null;
  datasetId?: string | null;
  datasetSnapshotId?: string | null;
  /** Frozen dataset snapshot that the API has confirmed as runnable. */
  dataset_snapshot_id?: string | null;
  /** True only when the API confirms that the current dataset can run analysis. */
  analysis_available?: boolean;
  /** Runtime capabilities that the API has implemented for this snapshot. */
  implemented_capabilities?: string[];
  /** Suggested questions from capabilities */
  suggestedQuestions?: string[];
  suggested_questions?: string[];
  /** Provider/database status reported by the API. */
  database_status?: string;
  db_tickers_count?: number;
  supported_operations?: string[];
  journal_mode?: string;
  limitation_code?: string | null;
  goldVersion?: string | null;
  entities: Entity[];
  periods: Period[];
  metrics: Metric[];
  topics: TopicPreset[];
  peerUniverse?: PeerUniverse | null;
  peerUniverses?: PeerUniverse[];
  macro: MacroCapability;
  ingestionTimestamp?: string | null;
  validationTimestamp?: string | null;
  source?: string | null;
  readiness?: string | null;
}
