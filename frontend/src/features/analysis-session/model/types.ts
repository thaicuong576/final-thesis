export type SpecialistId = 'company' | 'peer' | 'macro';

export type SpecialistStatus =
  | 'PREPARING' // "Đang chuẩn bị"
  | 'ANALYZING' // "Đang phân tích"
  | 'OUTPUT_CREATED' // "Đã tạo kết quả"
  | 'REVIEWING' // "Đang kiểm tra"
  | 'REVISING' // "Đang hiệu chỉnh"
  | 'COMPLETED'; // "Đã hoàn tất"

export interface ObservableActivity {
  id: string;
  timestamp?: string;
  description: string;
  type: 'DATA_RETRIEVAL' | 'VALIDATION' | 'INSIGHT_GENERATION' | 'REVISION';
}

export interface SpecialistArtifactSummary {
  headline: string;
  findings: string[];
  evidenceCount: number;
  version: number;
}

export interface ReviewFeedback {
  reviewer: string; // "Điều phối"
  critiqueSummary: string;
  status: 'PENDING_REVISION' | 'RESOLVED';
}

export interface RevisionRound {
  round: number;
  maxRounds: number;
  reason: string;
  activities: ObservableActivity[];
  completedAt?: string;
}

export interface SpecialistInvocation {
  id: string;
  specialistId: SpecialistId;
  label: string;
  assignment: string;
  status: SpecialistStatus;
  statusLabel: string;
  observationSummary: string;
  activities: ObservableActivity[];
  artifact?: SpecialistArtifactSummary;
  review?: ReviewFeedback;
  revision?: RevisionRound;
}

export type OrchestratorPhase =
  | 'INITIALIZING'
  | 'DISPATCHING'
  | 'EXECUTING'
  | 'REVIEWING'
  | 'REVISING'
  | 'SYNTHESIZING'
  | 'READY_FOR_REPORT';

export interface OrchestratorEntry {
  id: string;
  role: 'orchestrator';
  senderLabel: string;
  message: string;
  timestamp?: string;
  phase: OrchestratorPhase;
}

export interface AnalysisSession {
  sessionId: string;
  rawQuestion: string;
  datasetName: string;
  scopeSignature: string;
  currentPhase: OrchestratorPhase;
  phaseLabel: string;
  orchestratorEntries: OrchestratorEntry[];
  invocations: SpecialistInvocation[]; // Strictly only invoked specialists
  reportReady: boolean;
}
