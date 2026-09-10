export type MacroCapabilityStatus = 'AVAILABLE' | 'LIMITED' | 'UNAVAILABLE';

export interface Entity {
  id: string;
  ticker: string;
  name: string;
}

export interface Period {
  id: string;
  label: string;
  quarter: number;
  year: number;
}

export interface Metric {
  id: string;
  acronym: string;
  label: string;
  topicId: string;
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
}

export interface MacroCapability {
  status: MacroCapabilityStatus;
  minimumContractSatisfied: boolean;
  summary: string;
  details: string;
}

export interface AnalysisCapabilities {
  goldVersion: string;
  entities: Entity[];
  periods: Period[];
  metrics: Metric[];
  topics: TopicPreset[];
  peerUniverse: PeerUniverse;
  macro: MacroCapability;
  financialDataPeriod: string;
  ingestionTimestamp: string;
  validationTimestamp: string;
  source: string;
  readiness: string;
}
