import type { AnalysisSessionEvent } from '../model/types';

export const mockCompanyOnlyEvents: AnalysisSessionEvent[] = [
  {
    eventId: 'evt-c-01',
    sequence: 1,
    occurredAtMs: 0,
    type: 'USER_REQUEST_CONFIRMED',
    payload: {
      rawQuestion: 'ROE của TCB thay đổi thế nào trong năm 2024?',
      datasetName: 'Ngân hàng Việt Nam 2024',
      scopeSignature: 'TCB · Q1–Q4/2024 · ROE'
    }
  },
  {
    eventId: 'evt-c-02',
    sequence: 2,
    occurredAtMs: 500,
    type: 'PLANNING_STARTED',
    payload: {
      message: 'Đang chuẩn bị yêu cầu phân tích và xác định kế hoạch chuyên môn...'
    }
  },
  {
    eventId: 'evt-c-03',
    sequence: 3,
    occurredAtMs: 1200,
    type: 'PLAN_CREATED',
    payload: {
      requiredSpecialists: ['company'],
      planSummary: 'Phân tích doanh nghiệp đơn mục tiêu',
      message:
        'Đã xác định phạm vi TCB · Q1–Q4/2024 · ROE. Yêu cầu này cần phân tích doanh nghiệp. Đã giao 1 nhiệm vụ chuyên môn.'
    }
  },
  {
    eventId: 'evt-c-04',
    sequence: 4,
    occurredAtMs: 1600,
    type: 'SPECIALIST_INVOKED',
    payload: {
      invocationId: 'inv-company',
      specialistId: 'company',
      label: 'Phân tích doanh nghiệp',
      assignment: 'Phân tích diễn biến ROE của TCB trong năm 2024'
    }
  },
  {
    eventId: 'evt-c-05',
    sequence: 5,
    occurredAtMs: 2200,
    type: 'SPECIALIST_STARTED',
    payload: {
      invocationId: 'inv-company'
    }
  },
  {
    eventId: 'evt-c-06',
    sequence: 6,
    occurredAtMs: 3000,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-company',
      activity: {
        id: 'act-c-1',
        description: 'Đã truy xuất dữ liệu ROE của TCB (Q1–Q4/2024)',
        type: 'DATA_RETRIEVAL'
      }
    }
  },
  {
    eventId: 'evt-c-07',
    sequence: 7,
    occurredAtMs: 3800,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-company',
      activity: {
        id: 'act-c-2',
        description: 'Đã kiểm tra 4 quan sát hợp lệ cho ROE',
        type: 'VALIDATION'
      }
    }
  },
  {
    eventId: 'evt-c-08',
    sequence: 8,
    occurredAtMs: 4600,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-company',
      activity: {
        id: 'act-c-3',
        description: 'Đã tính toán biên sinh lời và phân rã các nhân tố ROE',
        type: 'DATA_RETRIEVAL'
      }
    }
  },
  {
    eventId: 'evt-c-09',
    sequence: 9,
    occurredAtMs: 5400,
    type: 'SPECIALIST_OUTPUT_CREATED',
    payload: {
      invocationId: 'inv-company',
      artifact: {
        headline: '3 nhận định · 4 quan sát tài chính',
        findings: [
          'TCB duy trì hiệu quả sinh lời vững chắc trong năm 2024 với ROE cải thiện qua từng quý.',
          'Biên thu nhập lãi thuần và kiểm soát chi phí hoạt động đóng góp tích cực vào tỷ suất sinh lời.',
          'Chất lượng tài sản và bộ đệm dự phòng rủi ro bảo đảm tỷ lệ an toàn vốn cao.'
        ],
        evidenceCount: 6,
        version: 1
      }
    }
  },
  {
    eventId: 'evt-c-10',
    sequence: 10,
    occurredAtMs: 6000,
    type: 'SPECIALIST_COMPLETED',
    payload: {
      invocationId: 'inv-company'
    }
  },
  {
    eventId: 'evt-c-11',
    sequence: 11,
    occurredAtMs: 6600,
    type: 'REVIEW_STARTED',
    payload: {
      message: 'Đã nhận đủ kết quả từ chuyên môn và hoàn tất kiểm tra tính nhất quán.'
    }
  },
  {
    eventId: 'evt-c-12',
    sequence: 12,
    occurredAtMs: 7400,
    type: 'SYNTHESIS_STARTED',
    payload: {
      message: 'Tôi đang tổng hợp các nhận định và bằng chứng vào cấu trúc phân tích.'
    }
  },
  {
    eventId: 'evt-c-13',
    sequence: 13,
    occurredAtMs: 8200,
    type: 'REPORT_READY',
    payload: {
      message: 'Đã hoàn tất kiểm tra và tổng hợp kết quả phân tích. Báo cáo đã sẵn sàng.'
    }
  }
];
