export type SpecialistId = string;

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
  | 'READY_FOR_REPORT'
  | 'BLOCKED';

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

// Strongly typed payload interfaces
export interface UserRequestConfirmedPayload {
  rawQuestion: string;
  datasetName: string;
  scopeSignature: string;
}

export interface PlanningStartedPayload {
  message?: string;
}

export interface PlanCreatedPayload {
  requiredSpecialists: SpecialistId[];
  planSummary: string;
  message: string;
}

export interface SpecialistInvokedPayload {
  invocationId: string;
  specialistId: SpecialistId;
  label: string;
  assignment: string;
}

export interface SpecialistStartedPayload {
  invocationId: string;
}

export interface SpecialistActivityPayload {
  invocationId: string;
  activity: ObservableActivity;
}

export interface SpecialistOutputCreatedPayload {
  invocationId: string;
  artifact: SpecialistArtifactSummary;
}

export interface SpecialistCompletedPayload {
  invocationId: string;
}

export interface ReviewStartedPayload {
  message?: string;
}

export interface ReviewFeedbackCreatedPayload {
  invocationId: string;
  review: ReviewFeedback;
}

export interface RevisionRequestedPayload {
  invocationId: string;
  round: number;
  maxRounds: number;
  reason: string;
  orchestratorMessage: string;
}

export interface RevisionActivityPayload {
  invocationId: string;
  activity: ObservableActivity;
}

export interface RevisionCompletedPayload {
  invocationId: string;
  artifact?: SpecialistArtifactSummary;
}

export interface SynthesisStartedPayload {
  message?: string;
}

export interface SynthesisCompletedPayload {
  message?: string;
}

export interface ReportReadyPayload {
  message?: string;
}

export interface RunBlockedPayload {
  reason: string;
}

export type TraceActor = 'orchestrator' | 'company' | 'sector' | 'macro' | 'critic' | 'verifier' | 'system';

export type TraceKind =
  | 'plan'
  | 'assign'
  | 'tool_result'
  | 'draft'
  | 'verify'
  | 'compose'
  | 'critique_issue'
  | 'cross_level_finding'
  | 'revision'
  | 'accept'
  | 'report_ready'
  | 'blocked';

export interface TraceStep {
  step_id: string;
  seq: number;
  t_ms: number;
  actor: TraceActor;
  recipient: TraceActor | null;
  kind: TraceKind;
  summary: string;
  detail: Record<string, unknown>;
}

export interface RunTrace {
  run_id: string;
  status: string;
  query: string;
  created_at: string;
  duration_ms: number;
  arm: string | null;
  steps: TraceStep[];
}

// Event Contract: Strongly typed discriminated union
export type AnalysisSessionEvent =
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'USER_REQUEST_CONFIRMED'; payload: UserRequestConfirmedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'PLANNING_STARTED'; payload: PlanningStartedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'PLAN_CREATED'; payload: PlanCreatedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'SPECIALIST_INVOKED'; payload: SpecialistInvokedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'SPECIALIST_STARTED'; payload: SpecialistStartedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'SPECIALIST_ACTIVITY'; payload: SpecialistActivityPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'SPECIALIST_OUTPUT_CREATED'; payload: SpecialistOutputCreatedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'SPECIALIST_COMPLETED'; payload: SpecialistCompletedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'REVIEW_STARTED'; payload: ReviewStartedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'REVIEW_FEEDBACK_CREATED'; payload: ReviewFeedbackCreatedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'REVISION_REQUESTED'; payload: RevisionRequestedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'REVISION_ACTIVITY'; payload: RevisionActivityPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'REVISION_COMPLETED'; payload: RevisionCompletedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'SYNTHESIS_STARTED'; payload: SynthesisStartedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'SYNTHESIS_COMPLETED'; payload: SynthesisCompletedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'REPORT_READY'; payload: ReportReadyPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'RUN_BLOCKED'; payload: RunBlockedPayload }
  | { eventId: string; sequence: number; occurredAtMs: number; type: 'TRACE_STEP'; payload: TraceStep };

export type AnalysisSessionEventType = AnalysisSessionEvent['type'];

