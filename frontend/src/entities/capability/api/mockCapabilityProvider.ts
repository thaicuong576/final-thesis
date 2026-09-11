import type { AnalysisCapabilities } from '../model/types';

export const mockCapabilities: AnalysisCapabilities = {
  snapshotId: 'capabilities-gold-2026-09-11T09:30:00+07:00',
  goldVersion: '0.9',
  entities: [
    { id: 'acb', ticker: 'ACB', name: 'Ngân hàng Á Châu' },
    { id: 'tcb', ticker: 'TCB', name: 'Ngân hàng Kỹ thương Việt Nam' },
    { id: 'vpb', ticker: 'VPB', name: 'Ngân hàng Việt Nam Thịnh Vượng' },
    { id: 'mbb', ticker: 'MBB', name: 'Ngân hàng Quân Đội' },
    { id: 'vcb', ticker: 'VCB', name: 'Ngân hàng Ngoại thương Việt Nam' }
  ],
  periods: [
    { id: '2024-q1', quarter: 1, year: 2024 },
    { id: '2024-q2', quarter: 2, year: 2024 },
    { id: '2024-q3', quarter: 3, year: 2024 },
    { id: '2024-q4', quarter: 4, year: 2024 }
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
  ingestionTimestamp: '2026-09-11T08:45:00+07:00',
  validationTimestamp: '2026-09-11T09:30:00+07:00',
  source: 'Nguồn năng lực Gold · dữ liệu mô phỏng cho frontend',
  readiness: 'Đã sẵn sàng cho kiểm tra phạm vi phía giao diện'
};

export async function getMockCapabilities(): Promise<AnalysisCapabilities> {
  return mockCapabilities;
}
