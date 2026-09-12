import type {
  AnalysisSessionEvent,
  AnalysisSessionViewModel,
  OrchestratorPhase,
  SpecialistSessionState,
  ThreadItem
} from './types';

const phaseLabelMap: Record<OrchestratorPhase, string> = {
  INITIALIZING: 'Đang chuẩn bị',
  PLANNING: 'Đang lập kế hoạch phân tích',
  DISPATCHING: 'Đã giao nhiệm vụ',
  EXECUTING: 'Đang phân tích',
  REVIEWING: 'Đang kiểm tra tính nhất quán',
  REVISING: 'Đang hiệu chỉnh chuyên môn liên quan',
  SYNTHESIZING: 'Đang tổng hợp kết quả',
  READY_FOR_REPORT: 'Sẵn sàng tạo báo cáo'
};

/**
 * Pure deterministic projector that reduces an ordered sequence of AnalysisSessionEvent
 * into a single unified AnalysisSessionViewModel.
 *
 * Rules:
 * - Pure function: no timers, no random values, no network calls, no React state.
 * - Same event list -> exactly identical output every single run.
 * - Prefix property: projectAnalysisSession(events.slice(0, n)) produces valid intermediate state.
 */
export function projectAnalysisSession(
  events: AnalysisSessionEvent[]
): AnalysisSessionViewModel {
  const specialistSessions: Record<string, SpecialistSessionState> = {};
  const threadItems: ThreadItem[] = [];

  let rawQuestion = '';
  let datasetName = 'Ngân hàng Việt Nam 2024';
  let scopeSignature = '';
  let currentPhase: OrchestratorPhase = 'INITIALIZING';
  let reportReady = false;

  // Sort events deterministically by sequence just in case
  const sortedEvents = [...events].sort((a, b) => a.sequence - b.sequence);

  for (const event of sortedEvents) {
    switch (event.type) {
      case 'USER_REQUEST_CONFIRMED': {
        rawQuestion = event.payload.rawQuestion || rawQuestion;
        datasetName = event.payload.datasetName || datasetName;
        scopeSignature = event.payload.scopeSignature || scopeSignature;
        threadItems.push({
          id: event.eventId,
          type: 'USER_MESSAGE',
          question: rawQuestion,
          occurredAtMs: event.occurredAtMs
        });
        break;
      }

      case 'PLANNING_STARTED': {
        currentPhase = 'PLANNING';
        threadItems.push({
          id: event.eventId,
          type: 'ORCHESTRATOR_MESSAGE',
          senderLabel: 'Điều phối',
          message:
            event.payload.message || 'Đang xác định phạm vi và kế hoạch phân tích...',
          phase: 'PLANNING',
          occurredAtMs: event.occurredAtMs
        });
        break;
      }

      case 'PLAN_CREATED': {
        currentPhase = 'DISPATCHING';
        threadItems.push({
          id: event.eventId,
          type: 'ORCHESTRATOR_MESSAGE',
          senderLabel: 'Điều phối',
          message: event.payload.message,
          phase: 'DISPATCHING',
          occurredAtMs: event.occurredAtMs
        });
        break;
      }

      case 'SPECIALIST_INVOKED': {
        const { invocationId, specialistId, label, assignment } = event.payload;
        specialistSessions[invocationId] = {
          invocationId,
          specialistId,
          label,
          assignment,
          status: 'PREPARING',
          statusLabel: 'Đang bắt đầu',
          observationSummary: 'Đã nhận nhiệm vụ từ Điều phối',
          activities: [],
          artifactHistory: []
        };
        // Anchor the specialist card inline in the thread at this exact chronological moment!
        threadItems.push({
          id: event.eventId,
          type: 'SPECIALIST_INVOCATION',
          invocationId,
          specialistId,
          label,
          assignment,
          occurredAtMs: event.occurredAtMs
        });
        break;
      }

      case 'SPECIALIST_STARTED': {
        const session = specialistSessions[event.payload.invocationId];
        if (session) {
          session.status = 'ANALYZING';
          session.statusLabel = 'Đang phân tích';
          session.observationSummary = 'Đang thực hiện phân tích số liệu';
        }
        break;
      }

      case 'SPECIALIST_ACTIVITY': {
        const session = specialistSessions[event.payload.invocationId];
        if (session) {
          session.activities.push(event.payload.activity);
          session.status = 'ANALYZING';
          session.statusLabel = 'Đang phân tích';
          session.observationSummary = event.payload.activity.description;
        }
        break;
      }

      case 'SPECIALIST_OUTPUT_CREATED': {
        const session = specialistSessions[event.payload.invocationId];
        if (session) {
          session.artifact = event.payload.artifact;
          session.artifactHistory.push(event.payload.artifact);
          session.status = 'OUTPUT_CREATED';
          session.statusLabel = 'Đã tạo kết quả';
          session.observationSummary = `${event.payload.artifact.headline} · ${event.payload.artifact.evidenceCount} dẫn chứng`;
        }
        break;
      }

      case 'SPECIALIST_COMPLETED': {
        const session = specialistSessions[event.payload.invocationId];
        if (session) {
          session.status = 'COMPLETED';
          session.statusLabel =
            session.artifactHistory.length > 1 ? 'Hiệu chỉnh hoàn tất' : 'Đã hoàn tất';
        }
        break;
      }

      case 'REVIEW_STARTED': {
        currentPhase = 'REVIEWING';
        threadItems.push({
          id: event.eventId,
          type: 'ORCHESTRATOR_MESSAGE',
          senderLabel: 'Điều phối',
          message:
            event.payload.message ||
            'Đã nhận kết quả từ các chuyên môn và đang kiểm tra tính nhất quán.',
          phase: 'REVIEWING',
          occurredAtMs: event.occurredAtMs
        });
        break;
      }

      case 'REVIEW_FEEDBACK_CREATED': {
        const session = specialistSessions[event.payload.invocationId];
        if (session) {
          session.review = event.payload.review;
        }
        break;
      }

      case 'REVISION_REQUESTED': {
        currentPhase = 'REVISING';
        const session = specialistSessions[event.payload.invocationId];
        if (session) {
          session.status = 'REVISING';
          session.statusLabel = `Đang hiệu chỉnh · vòng ${event.payload.round}/${event.payload.maxRounds}`;
          session.observationSummary = event.payload.reason;
          session.revision = {
            round: event.payload.round,
            maxRounds: event.payload.maxRounds,
            reason: event.payload.reason,
            activities: []
          };
        }
        threadItems.push({
          id: event.eventId,
          type: 'ORCHESTRATOR_MESSAGE',
          senderLabel: 'Điều phối',
          message: event.payload.orchestratorMessage,
          phase: 'REVISING',
          occurredAtMs: event.occurredAtMs
        });
        break;
      }

      case 'REVISION_ACTIVITY': {
        const session = specialistSessions[event.payload.invocationId];
        if (session) {
          session.activities.push(event.payload.activity);
          if (session.revision) {
            session.revision.activities.push(event.payload.activity);
          }
          session.observationSummary = event.payload.activity.description;
        }
        break;
      }

      case 'REVISION_COMPLETED': {
        const session = specialistSessions[event.payload.invocationId];
        if (session) {
          session.status = 'COMPLETED';
          session.statusLabel = 'Hiệu chỉnh hoàn tất';
          if (event.payload.artifact) {
            session.artifact = event.payload.artifact;
            session.artifactHistory.push(event.payload.artifact);
            session.observationSummary = `${event.payload.artifact.headline} · ${event.payload.artifact.evidenceCount} dẫn chứng`;
          }
          if (session.review) {
            session.review.status = 'RESOLVED';
          }
        }
        break;
      }

      case 'SYNTHESIS_STARTED': {
        currentPhase = 'SYNTHESIZING';
        threadItems.push({
          id: event.eventId,
          type: 'ORCHESTRATOR_MESSAGE',
          senderLabel: 'Điều phối',
          message:
            event.payload.message ||
            'Đã hoàn tất hiệu chỉnh. Tôi đang tổng hợp các nhận định và bằng chứng.',
          phase: 'SYNTHESIZING',
          occurredAtMs: event.occurredAtMs
        });
        break;
      }

      case 'SYNTHESIS_COMPLETED': {
        currentPhase = 'SYNTHESIZING';
        if (event.payload.message) {
          threadItems.push({
            id: event.eventId,
            type: 'ORCHESTRATOR_MESSAGE',
            senderLabel: 'Điều phối',
            message: event.payload.message,
            phase: 'SYNTHESIZING',
            occurredAtMs: event.occurredAtMs
          });
        }
        break;
      }

      case 'REPORT_READY': {
        currentPhase = 'READY_FOR_REPORT';
        reportReady = true;
        threadItems.push({
          id: event.eventId,
          type: 'ORCHESTRATOR_MESSAGE',
          senderLabel: 'Điều phối',
          message:
            event.payload.message ||
            'Đã hoàn tất kiểm tra và tổng hợp kết quả phân tích. Báo cáo đã sẵn sàng.',
          phase: 'READY_FOR_REPORT',
          occurredAtMs: event.occurredAtMs
        });
        threadItems.push({
          id: `${event.eventId}-cta`,
          type: 'REPORT_READY_ACTION',
          message: 'Báo cáo phân tích đã sẵn sàng',
          occurredAtMs: event.occurredAtMs
        });
        break;
      }
    }
  }

  const invocations = Object.values(specialistSessions);

  return {
    sessionId: `session-audit-${events.length > 0 ? events[0].eventId : 'empty'}`,
    rawQuestion,
    datasetName,
    scopeSignature,
    currentPhase,
    phaseLabel: phaseLabelMap[currentPhase],
    threadItems,
    specialistSessions,
    invocations,
    reportReady
  };
}
