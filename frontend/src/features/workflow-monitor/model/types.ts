import type { AnalyticalCapabilityId } from '../../analysis-composer/model/types';

export type WorkflowOverallStatus =
  | 'PREPARING'
  | 'RUNNING'
  | 'REVISING'
  | 'SYNTHESIZING'
  | 'READY_FOR_REPORT';

export type SpecialistStatus =
  | 'PREPARING'
  | 'ANALYZING'
  | 'PRODUCED_FINDINGS'
  | 'UNDER_REVIEW'
  | 'REVISING'
  | 'COMPLETED';

export interface ObservableActivity {
  id: string;
  timestamp: string;
  action: string;
  dataSource: string;
  status: 'COMPLETED' | 'IN_PROGRESS';
}

export interface FindingArtifact {
  id: string;
  title: string;
  metric?: string;
  value?: string;
  evidenceSource: string;
  confidence: 'HIGH' | 'MEDIUM';
}

export interface RevisionDetail {
  iteration: number;
  maxIterations: number;
  orchestratorFeedback: string;
  status: 'IN_PROGRESS' | 'RESOLVED';
  resolvedNote?: string;
}

export interface SpecialistRunState {
  id: AnalyticalCapabilityId;
  name: string;
  roleDescription: string;
  targetEntity?: string;
  status: SpecialistStatus;
  statusLabel: string;
  currentActivityDescription: string;
  assignedTask: string;
  observableActivities: ObservableActivity[];
  findings: FindingArtifact[];
  revision?: RevisionDetail;
  completedAt?: string;
}

export interface OrchestratorRunState {
  planObjective: string;
  activeSpecialistIds: AnalyticalCapabilityId[];
  overallStatus: WorkflowOverallStatus;
  overallStatusLabel: string;
  planningRationale: string;
  reviewSummary?: string;
  synthesisSummary?: string;
  revisionRound?: number;
  totalRevisionsCount?: number;
}

export interface WorkflowRun {
  runId: string;
  createdAt: string;
  question: string;
  scopeSignature: string;
  datasetName: string;
  orchestrator: OrchestratorRunState;
  specialists: SpecialistRunState[];
}

export type DemoScenarioId = 'COMPANY_ONLY' | 'COMPANY_PEER' | 'TARGETED_REVISION' | 'BROAD_ANALYSIS';
