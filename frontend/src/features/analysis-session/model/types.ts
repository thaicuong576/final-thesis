export type SpecialistId = 'company' | 'peer' | 'macro';

export type SpecialistStatus =
  | 'PREPARING' // "Đang bắt đầu"
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

export interface SpecialistSessionState {
  invocationId: string;
  specialistId: SpecialistId;
  label: string;
  assignment: string;
  status: SpecialistStatus;
  statusLabel: string;
  observationSummary: string;
  activities: ObservableActivity[];
  artifact?: SpecialistArtifactSummary;
  artifactHistory: SpecialistArtifactSummary[];
  review?: ReviewFeedback;
  revision?: RevisionRound;
}

export type OrchestratorPhase =
  | 'INITIALIZING'
  | 'PLANNING'
  | 'DISPATCHING'
  | 'EXECUTING'
  | 'REVIEWING'
  | 'REVISING'
  | 'SYNTHESIZING'
  | 'READY_FOR_REPORT';

export interface OrchestratorMessageEntry {
  id: string;
  role: 'orchestrator';
  senderLabel: string;
  message: string;
  phase: OrchestratorPhase;
}

// Chronological thread items
export type ThreadItem =
  | {
      id: string;
      type: 'USER_MESSAGE';
      question: string;
      occurredAtMs: number;
    }
  | {
      id: string;
      type: 'ORCHESTRATOR_MESSAGE';
      senderLabel: string;
      message: string;
      phase: OrchestratorPhase;
      occurredAtMs: number;
    }
  | {
      id: string;
      type: 'SPECIALIST_INVOCATION';
      invocationId: string;
      specialistId: SpecialistId;
      label: string;
      assignment: string;
      occurredAtMs: number;
    }
  | {
      id: string;
      type: 'REPORT_READY_ACTION';
      message: string;
      occurredAtMs: number;
    };

export interface AnalysisSessionViewModel {
  sessionId: string;
  rawQuestion: string;
  datasetName: string;
  scopeSignature: string;
  currentPhase: OrchestratorPhase;
  phaseLabel: string;
  threadItems: ThreadItem[];
  specialistSessions: Record<string, SpecialistSessionState>;
  invocations: SpecialistSessionState[]; // Preserves ordered list of currently active specialist sessions
  reportReady: boolean;
}

// Event Contract
export type AnalysisSessionEventType =
  | 'USER_REQUEST_CONFIRMED'
  | 'PLANNING_STARTED'
  | 'PLAN_CREATED'
  | 'SPECIALIST_INVOKED'
  | 'SPECIALIST_STARTED'
  | 'SPECIALIST_ACTIVITY'
  | 'SPECIALIST_OUTPUT_CREATED'
  | 'SPECIALIST_COMPLETED'
  | 'REVIEW_STARTED'
  | 'REVIEW_FEEDBACK_CREATED'
  | 'REVISION_REQUESTED'
  | 'REVISION_ACTIVITY'
  | 'REVISION_COMPLETED'
  | 'SYNTHESIS_STARTED'
  | 'SYNTHESIS_COMPLETED'
  | 'REPORT_READY';

export interface AnalysisSessionEvent<TPayload = any> {
  eventId: string;
  sequence: number;
  occurredAtMs: number;
  type: AnalysisSessionEventType;
  payload: TPayload;
}
