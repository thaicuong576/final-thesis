import type { AnalysisSessionEvent } from '../model/types';

export const mockTargetedRevisionEvents: AnalysisSessionEvent[] = [
  {
    eventId: 'evt-tr-01',
    sequence: 1,
    occurredAtMs: 0,
    type: 'USER_REQUEST_CONFIRMED',
    payload: {
      rawQuestion: 'TCB sinh lời tốt hơn hay kém nhóm so sánh trong năm 2024?',
      datasetName: 'Ngân hàng Việt Nam 2024',
      scopeSignature: 'TCB · Q1–Q4/2024 · ROA · ROE'
    }
  },
  {
    eventId: 'evt-tr-02',
    sequence: 2,
    occurredAtMs: 500,
    type: 'PLANNING_STARTED',
    payload: {
      message: 'Đang chuẩn bị yêu cầu phân tích và xác định kế hoạch chuyên môn...'
    }
  },
  {
    eventId: 'evt-tr-03',
    sequence: 3,
    occurredAtMs: 1200,
    type: 'PLAN_CREATED',
    payload: {
      requiredSpecialists: ['company', 'peer'],
      planSummary: 'Phân tích đối sánh tương quan kèm kiểm tra chu kỳ',
      message:
        'Đã xác định phạm vi TCB · Q1–Q4/2024 · ROA · ROE. Yêu cầu này cần phân tích doanh nghiệp và nhóm tham chiếu. Đã giao 2 nhiệm vụ chuyên môn.'
    }
  },
  {
    eventId: 'evt-tr-04',
    sequence: 4,
    occurredAtMs: 1600,
    type: 'SPECIALIST_INVOKED',
    payload: {
      invocationId: 'inv-company',
      specialistId: 'company',
      label: 'Phân tích doanh nghiệp',
      assignment: 'Phân tích diễn biến ROA, ROE của TCB trong Q1–Q4/2024'
    }
  },
  {
    eventId: 'evt-tr-05',
    sequence: 5,
    occurredAtMs: 1800,
    type: 'SPECIALIST_INVOKED',
    payload: {
      invocationId: 'inv-peer',
      specialistId: 'peer',
      label: 'Nhóm tham chiếu',
      assignment: 'Đối sánh ROA, ROE với Nhóm tham chiếu 5 ngân hàng cùng kỳ'
    }
  },
  {
    eventId: 'evt-tr-06',
    sequence: 6,
    occurredAtMs: 2300,
    type: 'SPECIALIST_STARTED',
    payload: {
      invocationId: 'inv-company'
    }
  },
  {
    eventId: 'evt-tr-07',
    sequence: 7,
    occurredAtMs: 2400,
    type: 'SPECIALIST_STARTED',
    payload: {
      invocationId: 'inv-peer'
    }
  },
  {
    eventId: 'evt-tr-08',
    sequence: 8,
    occurredAtMs: 3200,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-company',
      activity: {
        id: 'act-tr-c1',
        description: 'Đã truy xuất dữ liệu tài chính TCB (Q1–Q4/2024)',
        type: 'DATA_RETRIEVAL'
      }
    }
  },
  {
    eventId: 'evt-tr-09',
    sequence: 9,
    occurredAtMs: 3400,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-peer',
      activity: {
        id: 'act-tr-p1',
        description: 'Đã truy xuất benchmark cùng kỳ của Nhóm tham chiếu 5 ngân hàng',
        type: 'DATA_RETRIEVAL'
      }
    }
  },
  {
    eventId: 'evt-tr-10',
    sequence: 10,
    occurredAtMs: 4100,
    type: 'SPECIALIST_OUTPUT_CREATED',
    payload: {
      invocationId: 'inv-company',
      artifact: {
        headline: '3 nhận định · 4 quan sát tài chính',
        findings: [
          'TCB duy trì tỷ suất sinh lời ROA và ROE có đầy đủ quan sát trong 4 quý năm 2024.',
          'Dữ liệu chỉ tiêu phản ánh nhất quán với báo cáo tài chính đã công bố.',
          'Các giá trị số liệu được đối soát nguồn gốc từ chuỗi dữ liệu chuẩn hóa.'
        ],
        evidenceCount: 4,
        version: 1
      }
    }
  },
  {
    eventId: 'evt-tr-11',
    sequence: 11,
    occurredAtMs: 4300,
    type: 'SPECIALIST_COMPLETED',
    payload: {
      invocationId: 'inv-company'
    }
  },
  {
    eventId: 'evt-tr-12',
    sequence: 12,
    occurredAtMs: 4700,
    type: 'SPECIALIST_OUTPUT_CREATED',
    payload: {
      invocationId: 'inv-peer',
      artifact: {
        headline: '3 nhận định đối sánh v1 · 5 dẫn chứng',
        findings: [
          'TCB nằm trong nhóm ngân hàng có tỷ suất sinh lời cao hơn trung vị nhóm tham chiếu.',
          'Chỉ số ROA và ROE của TCB duy trì vị thế trên phân vị 50 (sử dụng dữ liệu tạm thời Q3).',
          'Dữ liệu đối sánh bước đầu phản ánh phân bố tương quan giữa các ngân hàng cùng nhóm.'
        ],
        evidenceCount: 5,
        version: 1
      }
    }
  },
  {
    eventId: 'evt-tr-13',
    sequence: 13,
    occurredAtMs: 5000,
    type: 'SPECIALIST_COMPLETED',
    payload: {
      invocationId: 'inv-peer'
    }
  },
  {
    eventId: 'evt-tr-14',
    sequence: 14,
    occurredAtMs: 5400,
    type: 'REVIEW_STARTED',
    payload: {
      message: 'Đã nhận đủ kết quả và đang kiểm tra tính nhất quán giữa các nhận định.'
    }
  },
  {
    eventId: 'evt-tr-15',
    sequence: 15,
    occurredAtMs: 5800,
    type: 'REVIEW_FEEDBACK_CREATED',
    payload: {
      invocationId: 'inv-peer',
      review: {
        reviewer: 'Điều phối',
        critiqueSummary:
          'Benchmark của nhận định thứ hai chưa cùng kỳ (Q3 thay vì Q4). Cần đồng bộ lại với chu kỳ chuẩn.',
        status: 'PENDING_REVISION'
      }
    }
  },
  {
    eventId: 'evt-tr-16',
    sequence: 16,
    occurredAtMs: 6200,
    type: 'REVISION_REQUESTED',
    payload: {
      invocationId: 'inv-peer',
      round: 1,
      maxRounds: 2,
      reason: 'Đồng bộ lại benchmark quý 4 cho nhóm tham chiếu',
      orchestratorMessage:
        'Tôi phát hiện một benchmark trong kết quả đối sánh chưa cùng kỳ (Q3 thay vì Q4). Tôi đã yêu cầu Nhóm tham chiếu kiểm tra lại.'
    }
  },
  {
    eventId: 'evt-tr-17',
    sequence: 17,
    occurredAtMs: 7000,
    type: 'REVISION_ACTIVITY',
    payload: {
      invocationId: 'inv-peer',
      activity: {
        id: 'act-tr-rev1',
        description: 'Đang truy xuất lại dữ liệu benchmark Q4 cho cùng kỳ',
        type: 'REVISION'
      }
    }
  },
  {
    eventId: 'evt-tr-18',
    sequence: 18,
    occurredAtMs: 7800,
    type: 'REVISION_ACTIVITY',
    payload: {
      invocationId: 'inv-peer',
      activity: {
        id: 'act-tr-rev2',
        description: 'Đang hiệu chỉnh nhận định đối sánh tương đối',
        type: 'REVISION'
      }
    }
  },
  {
    eventId: 'evt-tr-19',
    sequence: 19,
    occurredAtMs: 8600,
    type: 'REVISION_COMPLETED',
    payload: {
      invocationId: 'inv-peer',
      artifact: {
        headline: '3 nhận định đối sánh chuẩn hóa · 6 dẫn chứng',
        findings: [
          'TCB nằm trong nhóm ngân hàng có tỷ suất sinh lời cao hơn trung vị nhóm tham chiếu cả 4 quý.',
          'Chỉ số ROA và ROE của TCB duy trì vị thế trên phân vị 50 sau khi đồng bộ dữ liệu Q4/2024.',
          'Toàn bộ 6 dẫn chứng đối sánh đã được chuẩn hóa đồng nhất kỳ báo cáo.'
        ],
        evidenceCount: 6,
        version: 2
      }
    }
  },
  {
    eventId: 'evt-tr-20',
    sequence: 20,
    occurredAtMs: 9200,
    type: 'SYNTHESIS_STARTED',
    payload: {
      message:
        'Hiệu chỉnh dữ liệu đối sánh đã hoàn tất. Tôi đang tổng hợp kết quả phân tích.'
    }
  },
  {
    eventId: 'evt-tr-21',
    sequence: 21,
    occurredAtMs: 9800,
    type: 'SYNTHESIS_COMPLETED',
    payload: {
      message:
        'Đã hoàn thành cấu trúc hóa báo cáo và liên kết nguồn dữ liệu sau hiệu chỉnh.'
    }
  },
  {
    eventId: 'evt-tr-22',
    sequence: 22,
    occurredAtMs: 10400,
    type: 'REPORT_READY',
    payload: {
      message:
        'Đã hoàn tất kiểm tra và tổng hợp kết quả phân tích. Báo cáo đã sẵn sàng.'
    }
  }
];
