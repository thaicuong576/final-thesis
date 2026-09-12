import type { AnalysisCapabilities } from '@/entities/capability/model/types';
import type { ParseResult } from '../../analysis-composer/model/types';
import type {
  AnalysisSession,
  ObservableActivity,
  OrchestratorEntry,
  OrchestratorPhase,
  SpecialistInvocation
} from './types';

export interface CreateSessionOptions {
  withTargetedRevision?: boolean;
  phase?: OrchestratorPhase;
}

/**
 * Generates an observable AnalysisSession dynamically based on user ParseResult
 * and dataset capabilities.
 * Strictly adheres to query-adaptive visibility: only required specialists are created.
 */
export function createAnalysisSession(
  parseResult: ParseResult,
  capabilities: AnalysisCapabilities,
  options: CreateSessionOptions = {}
): AnalysisSession {
  const { rawQuestion, scope } = parseResult;
  const selectedCapIds = scope.analysisPlan.selectedCapabilities.map((c) => c.id);

  const hasCompany = selectedCapIds.includes('company');
  const hasPeer = selectedCapIds.includes('peer');
  const hasMacro = selectedCapIds.includes('macro');

  const withRevision = Boolean(options.withTargetedRevision && hasPeer);
  const currentPhase: OrchestratorPhase =
    options.phase || (withRevision ? 'REVISING' : 'READY_FOR_REPORT');

  const invocations: SpecialistInvocation[] = [];

  const entityNames =
    scope.entities.length > 0
      ? scope.entities.map((e) => e.ticker).join(', ')
      : 'doanh nghiệp';

  const metricNames =
    scope.metrics.length > 0
      ? scope.metrics.map((m) => m.acronym).join(', ')
      : 'các chỉ tiêu tài chính';

  const periodSig = scope.scopeSignature.split(' · ')[1] || 'chu kỳ phân tích';

  // 1. Company Specialist Invocation (Only if requested)
  if (hasCompany) {
    const companyActivities: ObservableActivity[] = [
      {
        id: 'act-c-1',
        description: `Đã truy xuất dữ liệu tài chính ${entityNames} (${periodSig})`,
        type: 'DATA_RETRIEVAL'
      },
      {
        id: 'act-c-2',
        description: `Đã kiểm tra 4 quan sát hợp lệ cho ${metricNames}`,
        type: 'VALIDATION'
      },
      {
        id: 'act-c-3',
        description: `Đã tính toán chỉ số và biên biến động tài chính`,
        type: 'DATA_RETRIEVAL'
      },
      {
        id: 'act-c-4',
        description: `Đã tạo 3 nhận định kèm dẫn chứng số liệu đã xác thực`,
        type: 'INSIGHT_GENERATION'
      }
    ];

    invocations.push({
      id: 'inv-company',
      specialistId: 'company',
      label: 'Phân tích doanh nghiệp',
      assignment: `Phân tích diễn biến ${metricNames} của ${entityNames} trong ${periodSig}`,
      status: 'COMPLETED',
      statusLabel: 'Đã hoàn tất',
      observationSummary: 'Đã truy xuất 4 quan sát hợp lệ',
      activities: companyActivities,
      artifact: {
        headline: `3 nhận định · 4 quan sát tài chính`,
        findings: [
          `${entityNames} duy trì hiệu quả sinh lời vững chắc trong ${periodSig}.`,
          `Biên thu nhập và chi phí hoạt động duy trì ở mức tối ưu.`,
          `Chất lượng tài sản và bộ đệm dự phòng rủi ro tuân thủ quy chuẩn.`
        ],
        evidenceCount: 6,
        version: 1
      }
    });
  }

  // 2. Peer / Reference Universe Specialist Invocation (Only if requested)
  if (hasPeer) {
    const peerLabel = capabilities.peerUniverse?.label || 'nhóm tham chiếu';

    if (withRevision && currentPhase === 'REVISING') {
      // Targeted Revision In-Progress State
      const peerActivities: ObservableActivity[] = [
        {
          id: 'act-p-1',
          description: `Đã truy xuất benchmark cùng kỳ của ${peerLabel}`,
          type: 'DATA_RETRIEVAL'
        },
        {
          id: 'act-p-2',
          description: `Đang truy xuất lại dữ liệu benchmark Q4 cho cùng kỳ`,
          type: 'REVISION'
        },
        {
          id: 'act-p-3',
          description: `Đang hiệu chỉnh nhận định đối sánh tương đối`,
          type: 'REVISION'
        }
      ];

      invocations.push({
        id: 'inv-peer',
        specialistId: 'peer',
        label: 'Nhóm tham chiếu',
        assignment: `Đối sánh ${metricNames} với ${peerLabel} cùng kỳ`,
        status: 'REVISING',
        statusLabel: 'Đang hiệu chỉnh · vòng 1/2',
        observationSummary: 'Đang chuẩn hóa lại benchmark cùng kỳ',
        activities: peerActivities,
        review: {
          reviewer: 'Điều phối',
          critiqueSummary:
            'Benchmark của nhận định thứ hai chưa cùng kỳ (Q3 thay vì Q4). Cần đồng bộ lại với chu kỳ chuẩn.',
          status: 'PENDING_REVISION'
        },
        revision: {
          round: 1,
          maxRounds: 2,
          reason: 'Đồng bộ lại benchmark quý 4 cho nhóm tham chiếu',
          activities: [
            {
              id: 'rev-act-1',
              description: 'Truy xuất lại benchmark Q4 cho nhóm tham chiếu',
              type: 'REVISION'
            },
            {
              id: 'rev-act-2',
              description: 'Cập nhật lại nhận định đối sánh v2 cùng kỳ',
              type: 'INSIGHT_GENERATION'
            }
          ]
        }
      });
    } else {
      // Completed or Post-Revision State
      const peerActivities: ObservableActivity[] = [
        {
          id: 'act-p-1',
          description: `Đã truy xuất benchmark cùng kỳ của ${peerLabel}`,
          type: 'DATA_RETRIEVAL'
        },
        {
          id: 'act-p-2',
          description: `Đã tính trung vị và độ phân tán của nhóm tham chiếu`,
          type: 'DATA_RETRIEVAL'
        },
        {
          id: 'act-p-3',
          description: `Đã tạo 3 nhận định đối sánh vị thế tương đối`,
          type: 'INSIGHT_GENERATION'
        }
      ];

      if (withRevision) {
        peerActivities.push({
          id: 'act-p-4',
          description: `Đã đồng bộ benchmark Q4 và tạo artifact v2 hoàn tất`,
          type: 'REVISION'
        });
      }

      invocations.push({
        id: 'inv-peer',
        specialistId: 'peer',
        label: 'Nhóm tham chiếu',
        assignment: `Đối sánh ${metricNames} với ${peerLabel} cùng kỳ`,
        status: 'COMPLETED',
        statusLabel: withRevision ? 'Hiệu chỉnh hoàn tất' : 'Đã tạo kết quả',
        observationSummary: '3 nhận định đối sánh · 6 dẫn chứng',
        activities: peerActivities,
        review: withRevision
          ? {
              reviewer: 'Điều phối',
              critiqueSummary:
                'Benchmark của nhận định thứ hai chưa cùng kỳ (Q3 thay vì Q4).',
              status: 'RESOLVED'
            }
          : undefined,
        revision: withRevision
          ? {
              round: 1,
              maxRounds: 2,
              reason: 'Đồng bộ lại benchmark quý 4 cho nhóm tham chiếu',
              activities: [
                {
                  id: 'rev-act-1',
                  description: 'Truy xuất lại benchmark Q4 cho nhóm tham chiếu',
                  type: 'REVISION'
                },
                {
                  id: 'rev-act-2',
                  description: 'Cập nhật nhận định đối sánh v2 cùng kỳ',
                  type: 'INSIGHT_GENERATION'
                }
              ]
            }
          : undefined,
        artifact: {
          headline: `3 nhận định đối sánh · 6 dẫn chứng`,
          findings: [
            `${entityNames} xếp vị trí nhóm đầu về chỉ số sinh lời so với trung vị ngành.`,
            `Biên sinh lời tài sản cao hơn 1.2x mức trung vị nhóm tham chiếu.`,
            `Quy mô bộ đệm nợ xấu nằm trong nửa trên của các ngân hàng đối sánh.`
          ],
          evidenceCount: 6,
          version: withRevision ? 2 : 1
        }
      });
    }
  }

  // 3. Macro Context Specialist Invocation (Only if requested)
  if (hasMacro) {
    const macroActivities: ObservableActivity[] = [
      {
        id: 'act-m-1',
        description: 'Đã đọc diễn biến lãi suất điều hành từ dữ liệu NHNN',
        type: 'DATA_RETRIEVAL'
      },
      {
        id: 'act-m-2',
        description: 'Đã truy xuất bối cảnh tăng trưởng tín dụng toàn hệ thống',
        type: 'DATA_RETRIEVAL'
      },
      {
        id: 'act-m-3',
        description: 'Đã tạo 2 nhận định bối cảnh chính sách tiền tệ',
        type: 'INSIGHT_GENERATION'
      }
    ];

    invocations.push({
      id: 'inv-macro',
      specialistId: 'macro',
      label: 'Bối cảnh vĩ mô',
      assignment: 'Tích hợp diễn biến chính sách tiền tệ và tăng trưởng tín dụng',
      status: 'COMPLETED',
      statusLabel: 'Đã tạo kết quả',
      observationSummary: '2 nhận định vĩ mô · 4 dẫn chứng',
      activities: macroActivities,
      artifact: {
        headline: '2 nhận định vĩ mô · 4 dẫn chứng',
        findings: [
          'Chính sách tiền tệ linh hoạt và lãi suất điều hành duy trì hỗ trợ thanh khoản.',
          'Tăng trưởng tín dụng toàn ngành đạt mục tiêu định hướng trong chu kỳ.'
        ],
        evidenceCount: 4,
        version: 1
      }
    });
  }

  // Orchestrator narrative entries
  const orchestratorEntries: OrchestratorEntry[] = [
    {
      id: 'orch-1',
      role: 'orchestrator',
      senderLabel: 'Điều phối',
      phase: 'INITIALIZING',
      message: 'Đang chuẩn bị yêu cầu phân tích.'
    },
    {
      id: 'orch-2',
      role: 'orchestrator',
      senderLabel: 'Điều phối',
      phase: 'DISPATCHING',
      message: `Đã xác định phạm vi ${scope.scopeSignature}. Yêu cầu này cần ${invocations
        .map((i) => i.label.toLowerCase())
        .join(' và ')}. Đã giao ${invocations.length} nhiệm vụ chuyên môn.`
    }
  ];

  if (currentPhase === 'REVISING') {
    orchestratorEntries.push(
      {
        id: 'orch-3',
        role: 'orchestrator',
        senderLabel: 'Điều phối',
        phase: 'EXECUTING',
        message: 'Đã nhận đủ kết quả và đang kiểm tra tính nhất quán giữa các nhận định.'
      },
      {
        id: 'orch-4',
        role: 'orchestrator',
        senderLabel: 'Điều phối',
        phase: 'REVISING',
        message:
          'Tôi phát hiện một benchmark trong kết quả đối sánh chưa cùng kỳ (Q3 thay vì Q4). Tôi đã yêu cầu Nhóm tham chiếu kiểm tra lại.'
      }
    );
  } else {
    orchestratorEntries.push({
      id: 'orch-3',
      role: 'orchestrator',
      senderLabel: 'Điều phối',
      phase: 'REVIEWING',
      message: 'Đã nhận đủ kết quả từ các chuyên môn và hoàn tất kiểm tra tính nhất quán.'
    });

    if (withRevision) {
      orchestratorEntries.push({
        id: 'orch-4',
        role: 'orchestrator',
        senderLabel: 'Điều phối',
        phase: 'SYNTHESIZING',
        message:
          'Hiệu chỉnh dữ liệu đối sánh đã hoàn tất. Tôi đang tổng hợp kết quả phân tích.'
      });
    } else {
      orchestratorEntries.push({
        id: 'orch-4',
        role: 'orchestrator',
        senderLabel: 'Điều phối',
        phase: 'SYNTHESIZING',
        message: 'Tôi đang tổng hợp các nhận định và bằng chứng vào cấu trúc phân tích.'
      });
    }

    orchestratorEntries.push({
      id: 'orch-5',
      role: 'orchestrator',
      senderLabel: 'Điều phối',
      phase: 'READY_FOR_REPORT',
      message: 'Đã hoàn tất kiểm tra và tổng hợp kết quả phân tích. Báo cáo đã sẵn sàng.'
    });
  }

  const phaseLabelMap: Record<OrchestratorPhase, string> = {
    INITIALIZING: 'Đang chuẩn bị',
    DISPATCHING: 'Đã giao nhiệm vụ',
    EXECUTING: 'Đang phân tích',
    REVIEWING: 'Đang kiểm tra tính nhất quán',
    REVISING: 'Đang hiệu chỉnh chuyên môn liên quan',
    SYNTHESIZING: 'Đang tổng hợp kết quả',
    READY_FOR_REPORT: 'Sẵn sàng tạo báo cáo'
  };

  return {
    sessionId: `session-${Date.now()}`,
    rawQuestion,
    datasetName: 'Ngân hàng Việt Nam 2024',
    scopeSignature: scope.scopeSignature,
    currentPhase,
    phaseLabel: phaseLabelMap[currentPhase],
    orchestratorEntries,
    invocations,
    reportReady: currentPhase === 'READY_FOR_REPORT'
  };
}
