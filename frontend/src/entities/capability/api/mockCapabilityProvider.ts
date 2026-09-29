import type { AnalysisCapabilities } from '../model/types';

export const mockCapabilities: AnalysisCapabilities = {
  snapshotId: 'capabilities-gold-2026-09-11T09:30:00+07:00',
  goldVersion: '0.9',
  entities: [
    { id: 'acb', ticker: 'ACB', name: 'Ngân hàng Á Châu', type: 'company' },
    { id: 'tcb', ticker: 'TCB', name: 'Ngân hàng Kỹ thương Việt Nam', type: 'company' },
    { id: 'vpb', ticker: 'VPB', name: 'Ngân hàng Việt Nam Thịnh Vượng', type: 'company' },
    { id: 'mbb', ticker: 'MBB', name: 'Ngân hàng Quân Đội', type: 'company' },
    { id: 'vcb', ticker: 'VCB', name: 'Ngân hàng Ngoại thương Việt Nam', type: 'company' }
  ],
  periods: [
    { id: '2024-q1', quarter: 1, year: 2024, label: 'Q1/2024' },
    { id: '2024-q2', quarter: 2, year: 2024, label: 'Q2/2024' },
    { id: '2024-q3', quarter: 3, year: 2024, label: 'Q3/2024' },
    { id: '2024-q4', quarter: 4, year: 2024, label: 'Q4/2024' }
  ],
  metrics: [
    {
      id: 'npl',
      acronym: 'NPL',
      label: 'Tỷ lệ nợ xấu',
      shortLabel: 'Nợ xấu',
      topicId: 'asset-quality',
      unit: '%',
      direction: 'lower_is_better',
      decimals: 2,
      group: 'asset_quality',
      groupLabel: 'Chất lượng tài sản'
    },
    {
      id: 'coverage',
      acronym: 'Coverage',
      label: 'Tỷ lệ bao phủ nợ xấu',
      shortLabel: 'Bao phủ nợ xấu',
      topicId: 'asset-quality',
      unit: '%',
      direction: 'higher_is_better',
      decimals: 2,
      group: 'asset_quality',
      groupLabel: 'Chất lượng tài sản'
    },
    {
      id: 'roa',
      acronym: 'ROA',
      label: 'Tỷ suất sinh lời trên tài sản',
      shortLabel: 'ROA',
      topicId: 'profitability',
      unit: '%',
      direction: 'higher_is_better',
      decimals: 2,
      group: 'profitability',
      groupLabel: 'Khả năng sinh lời'
    },
    {
      id: 'roe',
      acronym: 'ROE',
      label: 'Tỷ suất sinh lời trên vốn chủ sở hữu',
      shortLabel: 'ROE',
      topicId: 'profitability',
      unit: '%',
      direction: 'higher_is_better',
      decimals: 2,
      group: 'profitability',
      groupLabel: 'Khả năng sinh lời'
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
