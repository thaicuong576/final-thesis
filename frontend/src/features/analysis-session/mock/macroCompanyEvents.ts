import type { AnalysisSessionEvent } from '../model/types';

export const mockMacroCompanyEvents: AnalysisSessionEvent[] = [
  {
    eventId: 'evt-mc-01',
    sequence: 1,
    occurredAtMs: 0,
    type: 'USER_REQUEST_CONFIRMED',
    payload: {
      rawQuestion: 'Lãi suất điều hành liên quan thế nào đến TCB trong năm 2024?',
      datasetName: 'Ngân hàng Việt Nam 2024',
      scopeSignature: 'TCB · Q1–Q4/2024 · NPL · Coverage · ROA · ROE'
    }
  },
  {
    eventId: 'evt-mc-02',
    sequence: 2,
    occurredAtMs: 500,
    type: 'PLANNING_STARTED',
    payload: {
      message: 'Đang chuẩn bị yêu cầu phân tích và xác định kế hoạch chuyên môn...'
    }
  },
  {
    eventId: 'evt-mc-03',
    sequence: 3,
    occurredAtMs: 1200,
    type: 'PLAN_CREATED',
    payload: {
      requiredSpecialists: ['company', 'macro'],
      planSummary: 'Tích hợp vĩ mô và doanh nghiệp',
      message:
        'Đã xác định phạm vi TCB · Q1–Q4/2024 · NPL · Coverage · ROA · ROE. Yêu cầu này cần phân tích doanh nghiệp và bối cảnh vĩ mô. Đã giao 2 nhiệm vụ chuyên môn.'
    }
  },
  {
    eventId: 'evt-mc-04',
    sequence: 4,
    occurredAtMs: 1600,
    type: 'SPECIALIST_INVOKED',
    payload: {
      invocationId: 'inv-company',
      specialistId: 'company',
      label: 'Phân tích doanh nghiệp',
      assignment: 'Phân tích diễn biến NPL, Coverage, ROA, ROE của TCB trong Q1–Q4/2024'
    }
  },
  {
    eventId: 'evt-mc-05',
    sequence: 5,
    occurredAtMs: 1800,
    type: 'SPECIALIST_INVOKED',
    payload: {
      invocationId: 'inv-macro',
      specialistId: 'macro',
      label: 'Bối cảnh vĩ mô',
      assignment: 'Tích hợp diễn biến chính sách tiền tệ và tăng trưởng tín dụng'
    }
  },
  {
    eventId: 'evt-mc-06',
    sequence: 6,
    occurredAtMs: 2300,
    type: 'SPECIALIST_STARTED',
    payload: {
      invocationId: 'inv-company'
    }
  },
  {
    eventId: 'evt-mc-07',
    sequence: 7,
    occurredAtMs: 2400,
    type: 'SPECIALIST_STARTED',
    payload: {
      invocationId: 'inv-macro'
    }
  },
  {
    eventId: 'evt-mc-08',
    sequence: 8,
    occurredAtMs: 3200,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-company',
      activity: {
        id: 'act-mc-c1',
        description: 'Đã truy xuất dữ liệu chi phí vốn và biên lãi thuần của TCB',
        type: 'DATA_RETRIEVAL'
      }
    }
  },
  {
    eventId: 'evt-mc-09',
    sequence: 9,
    occurredAtMs: 3400,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-macro',
      activity: {
        id: 'act-mc-m1',
        description: 'Đã đọc diễn biến lãi suất điều hành từ dữ liệu NHNN',
        type: 'DATA_RETRIEVAL'
      }
    }
  },
  {
    eventId: 'evt-mc-10',
    sequence: 10,
    occurredAtMs: 4200,
    type: 'SPECIALIST_ACTIVITY',
    payload: {
      invocationId: 'inv-macro',
      activity: {
        id: 'act-mc-m2',
        description: 'Đã truy xuất bối cảnh tăng trưởng tín dụng toàn hệ thống',
        type: 'DATA_RETRIEVAL'
      }
    }
  },
  {
    eventId: 'evt-mc-11',
    sequence: 11,
    occurredAtMs: 5000,
    type: 'SPECIALIST_OUTPUT_CREATED',
    payload: {
      invocationId: 'inv-company',
      artifact: {
        headline: '3 nhận định · 4 quan sát tài chính',
        findings: [
          'Biên lãi thuần NIM của TCB duy trì ổn định nhờ tối ưu hóa chi phí vốn trong môi trường lãi suất thấp.',
          'Thu nhập từ dịch vụ và kinh doanh ngoại hối tiếp tục hỗ trợ tổng thu nhập hoạt động.',
          'Tỷ lệ bao nợ xấu duy trì ở ngưỡng an toàn trên 100%.'
        ],
        evidenceCount: 6,
        version: 1
      }
    }
  },
  {
    eventId: 'evt-mc-12',
    sequence: 12,
    occurredAtMs: 5200,
    type: 'SPECIALIST_OUTPUT_CREATED',
    payload: {
      invocationId: 'inv-macro',
      artifact: {
        headline: '2 nhận định vĩ mô · 4 dẫn chứng',
        findings: [
          'Chính sách tiền tệ linh hoạt và lãi suất điều hành duy trì hỗ trợ thanh khoản toàn hệ thống ngân hàng.',
          'Tăng trưởng tín dụng toàn ngành đạt mục tiêu định hướng trong chu kỳ 2024.'
        ],
        evidenceCount: 4,
        version: 1
      }
    }
  },
  {
    eventId: 'evt-mc-13',
    sequence: 13,
    occurredAtMs: 5800,
    type: 'SPECIALIST_COMPLETED',
    payload: {
      invocationId: 'inv-company'
    }
  },
  {
    eventId: 'evt-mc-14',
    sequence: 14,
    occurredAtMs: 5900,
    type: 'SPECIALIST_COMPLETED',
    payload: {
      invocationId: 'inv-macro'
    }
  },
  {
    eventId: 'evt-mc-15',
    sequence: 15,
    occurredAtMs: 6500,
    type: 'REVIEW_STARTED',
    payload: {
      message: 'Đã nhận đủ kết quả từ các chuyên môn và hoàn tất kiểm tra tính nhất quán.'
    }
  },
  {
    eventId: 'evt-mc-16',
    sequence: 16,
    occurredAtMs: 7300,
    type: 'SYNTHESIS_STARTED',
    payload: {
      message: 'Tôi đang tổng hợp các nhận định và bằng chứng vào cấu trúc phân tích.'
    }
  },
  {
    eventId: 'evt-mc-17',
    sequence: 17,
    occurredAtMs: 8100,
    type: 'REPORT_READY',
    payload: {
      message: 'Đã hoàn tất kiểm tra và tổng hợp kết quả phân tích. Báo cáo đã sẵn sàng.'
    }
  }
];
