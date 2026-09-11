export type DatasetReadiness = 'READY';
export type MacroAvailability = 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE';
export type DataSourceKind = 'structured' | 'documents';

export interface DatasetSummary {
  name: string;
  readiness: DatasetReadiness;
  entityCount: number;
  periodLabel: string;
  metricCount: number;
  documentCount: number;
  scope: {
    entities: string;
    peerUniverse: string;
    macro: MacroAvailability;
  };
}

export interface DataSourceSummary {
  id: string;
  kind: DataSourceKind;
  title: string;
  typeLabel: string;
  statusLabel: string;
  observationCount?: number;
  validObservationCount?: number;
  missingValueCount?: number;
  duplicateCount?: number;
  documentCount?: number;
  examples?: string[];
  updatedAt: string;
}

export interface AnalysisDataset {
  summary: DatasetSummary;
  entities: string[];
  periods: string[];
  metrics: string[];
  sources: DataSourceSummary[];
}
