import type { AnalysisCapabilities } from '../model/types';

export const mockCapabilities: AnalysisCapabilities = {
  goldVersion: 'Gold v0.9 · mô phỏng',
  entities: [
    { id: 'acb', ticker: 'ACB', name: 'Ngân hàng Á Châu' },
    { id: 'tcb', ticker: 'TCB', name: 'Ngân hàng Kỹ thương Việt Nam' },
    { id: 'vpb', ticker: 'VPB', name: 'Ngân hàng Việt Nam Thịnh Vượng' },
    { id: 'mbb', ticker: 'MBB', name: 'Ngân hàng Quân Đội' },
    { id: 'vcb', ticker: 'VCB', name: 'Ngân hàng Ngoại thương Việt Nam' }
  ],
  periods: [
    { id: '2024-q1', label: 'Q1/2024', quarter: 1, year: 2024 },
    { id: '2024-q2', label: 'Q2/2024', quarter: 2, year: 2024 },
    { id: '2024-q3', label: 'Q3/2024', quarter: 3, year: 2024 },
    { id: '2024-q4', label: 'Q4/2024', quarter: 4, year: 2024 }
  ],
  metrics: [
    { id: 'npl', acronym: 'NPL', label: 'Tỷ lệ nợ xấu', topicId: 'asset-quality' },
    {
      id: 'coverage',
      acronym: 'Coverage',
      label: 'Tỷ lệ bao phủ nợ xấu',
      topicId: 'asset-quality'
    },
    {
      id: 'roa',
      acronym: 'ROA',
      label: 'Tỷ suất sinh lời trên tài sản',
      topicId: 'profitability'
    },
    {
      id: 'roe',
      acronym: 'ROE',
      label: 'Tỷ suất sinh lời trên vốn chủ sở hữu',
      topicId: 'profitability'
    }
  ],
  topics: [
    { id: 'asset-quality', label: 'Chất lượng tài sản', metricIds: ['npl', 'coverage'] },
    { id: 'profitability', label: 'Khả năng sinh lời', metricIds: ['roa', 'roe'] }
  ],
  peerUniverse: {
    id: 'validated-bank-5',
    label: 'Nhóm tham chiếu 5 ngân hàng',
    entityIds: ['acb', 'tcb', 'vpb', 'mbb', 'vcb'],
    readonly: true,
    description: 'Phạm vi đối sánh cố định hiện tại, không đại diện toàn bộ ngành ngân hàng Việt Nam.'
  },
  macro: {
    status: 'LIMITED',
    minimumContractSatisfied: true,
    summary: 'Hợp đồng Macro tối thiểu đã đáp ứng; bối cảnh bổ sung còn thiếu.',
    details: 'Phân tích vẫn có thể chạy. Báo cáo phải công bố rõ các giới hạn của lớp dữ liệu vĩ mô.'
  },
  financialDataPeriod: 'Q1–Q4/2024',
  ingestionTimestamp: '11/09/2026 08:45 ICT · mô phỏng',
  validationTimestamp: '11/09/2026 09:30 ICT · mô phỏng',
  source: 'Gold capability fixture · dữ liệu mô phỏng cho frontend',
  readiness: 'Đã sẵn sàng cho kiểm tra phạm vi phía giao diện'
};

export async function getMockCapabilities(): Promise<AnalysisCapabilities> {
  return mockCapabilities;
}
