import type { Entity, Metric, Period } from '@/entities/capability/model/types';

export type AnalyticalCapabilityId = 'company' | 'peer' | 'macro';

export interface AnalyticalCapabilityItem {
  id: AnalyticalCapabilityId;
  label: string;
  description?: string;
  selected: boolean;
}

export interface AnalysisPlanPreview {
  selectedCapabilities: AnalyticalCapabilityItem[];
}

export interface ParsedScope {
  rawQuestion?: string;
  entities: Entity[];
  periods: Period[];
  metrics: Metric[];
  topicLabels: string[];
  scopeSignature: string;
  analysisPlan: AnalysisPlanPreview;
  referenceUniverseLabel?: string;
}

export interface ScopeMismatch {
  isMismatch: boolean;
  reason?: string;
  unsupportedEntities?: string[];
  unsupportedPeriods?: string[];
  unsupportedMetrics?: string[];
  availableCapabilitiesSummary: {
    periods: string;
    metrics: string;
    entities: string;
  };
}

export interface ParseResult {
  rawQuestion: string;
  scope: ParsedScope;
  mismatch: ScopeMismatch;
}

export type Screen1Mode = 'DEFAULT' | 'INTERPRETED' | 'MISMATCH';

export interface DatasetItem {
  id: string;
  name: string;
  status: 'READY' | 'NOT_CONNECTED' | 'PREPARING';
  statusLabel: string;
  entitiesSummary: string;
  periodsSummary: string;
  metricsSummary: string;
  macroSummary: string;
  provenance: string;
  isActive: boolean;
}
