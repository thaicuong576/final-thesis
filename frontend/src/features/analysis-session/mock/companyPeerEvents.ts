import type { AnalysisSessionEvent } from '../model/types';

export const mockCompanyPeerEvents: AnalysisSessionEvent[] = [
  {
    eventId: 'evt-cp-01',
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
    eventId: 'evt-cp-02',
    sequence: 2,
    occurredAtMs: 500,
    type: 'PLANNING_STARTED',
    payload: {
      message: 'Đang chuẩn bị yêu cầu phân tích và xác định kế hoạch chuyên môn...'
    }
  },
  {
    eventId: 'evt-cp-03',
    sequence: 3,
    occurredAtMs: 1200,
    type: 'PLAN_CREATED',
    payload: {
      requiredSpecialists: ['company', 'peer'],
      planSummary: 'Phân tích đối sánh tương đối',
      message:
        'Đã xác định phạm vi TCB · Q1–Q4/2024 · ROA · ROE. Yêu cầu này cần phân tích doanh nghiệp và nhóm tham chiếu. Đã giao 2 nhiệm vụ chuyên môn.'
    }
  },
  {
    eventId: 'evt-cp-04',
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
    eventId: 'evt-cp-05',
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
    eventId: 'evt-cp-06',
    sequence: 6,
    occurredAtMs: 2300,
    type: 'SPECIALIST_STARTED',
    payload: {
      invocationId: 'inv-company'
    }
  },
  {
    eventId: 'evt-cp-07',
    sequence: 7,
    occurredAtMs: 2400,
    type: 'SPECIALIST_STARTED',
    payload: {
      invocationId: 'inv-peer'
    }
  },
  {
    eventId: 'evt-cp-08',
    sequence: 8,
    occurredAtMs: 3200,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-company',
      activity: {
        id: 'act-cp-c1',
        description: 'Đã truy xuất dữ liệu tài chính TCB (Q1–Q4/2024)',
        type: 'DATA_RETRIEVAL'
      }
    }
  },
  {
    eventId: 'evt-cp-09',
    sequence: 9,
    occurredAtMs: 3400,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-peer',
      activity: {
        id: 'act-cp-p1',
        description: 'Đã truy xuất benchmark cùng kỳ của Nhóm tham chiếu 5 ngân hàng',
        type: 'DATA_RETRIEVAL'
      }
    }
  },
  {
    eventId: 'evt-cp-10',
    sequence: 10,
    occurredAtMs: 4200,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-company',
      activity: {
        id: 'act-cp-c2',
        description: 'Đã kiểm tra 4 quan sát hợp lệ cho ROA, ROE',
        type: 'VALIDATION'
      }
    }
  },
  {
    eventId: 'evt-cp-11',
    sequence: 11,
    occurredAtMs: 4400,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-peer',
      activity: {
        id: 'act-cp-p2',
        description: 'Đã tính trung vị và độ phân tán của nhóm tham chiếu',
        type: 'DATA_RETRIEVAL'
      }
    }
  },
  {
    eventId: 'evt-cp-12',
    sequence: 12,
    occurredAtMs: 5200,
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
    eventId: 'evt-cp-13',
    sequence: 13,
    occurredAtMs: 5400,
    type: 'SPECIALIST_OUTPUT_CREATED',
    payload: {
      invocationId: 'inv-peer',
      artifact: {
        headline: '3 nhận định đối sánh · 6 dẫn chứng',
        findings: [
          'TCB nằm trong nhóm ngân hàng có chỉ số sinh lời ROA và ROE cao hơn trung vị nhóm tham chiếu.',
          'Vị thế tương đối của ROA và ROE duy trì trên phân vị 50 của 5 ngân hàng cùng nhóm.',
          'Dữ liệu đối sánh được chuẩn hóa cùng chu kỳ kế toán với nhóm tham chiếu.'
        ],
        evidenceCount: 6,
        version: 1
      }
    }
  },
  {
    eventId: 'evt-cp-14',
    sequence: 14,
    occurredAtMs: 5900,
    type: 'SPECIALIST_COMPLETED',
    payload: {
      invocationId: 'inv-company'
    }
  },
  {
    eventId: 'evt-cp-15',
    sequence: 15,
    occurredAtMs: 6000,
    type: 'SPECIALIST_COMPLETED',
    payload: {
      invocationId: 'inv-peer'
    }
  },
  {
    eventId: 'evt-cp-16',
    sequence: 16,
    occurredAtMs: 6600,
    type: 'REVIEW_STARTED',
    payload: {
      message: 'Đã nhận đủ kết quả từ các chuyên môn và hoàn tất kiểm tra tính nhất quán.'
    }
  },
  {
    eventId: 'evt-cp-17',
    sequence: 17,
    occurredAtMs: 7400,
    type: 'SYNTHESIS_STARTED',
    payload: {
      message: 'Tôi đang tổng hợp các nhận định và bằng chứng vào cấu trúc phân tích.'
    }
  },
  {
    eventId: 'evt-cp-18',
    sequence: 18,
    occurredAtMs: 8000,
    type: 'SYNTHESIS_COMPLETED',
    payload: {
      message: 'Đã hoàn thành cấu trúc hóa báo cáo đối sánh và liên kết nguồn dữ liệu.'
    }
  },
  {
    eventId: 'evt-cp-19',
    sequence: 19,
    occurredAtMs: 8600,
    type: 'REPORT_READY',
    payload: {
      message: 'Đã hoàn tất kiểm tra và tổng hợp kết quả phân tích. Báo cáo đã sẵn sàng.'
    }
  }
];
