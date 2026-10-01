import type { AnalysisCapabilities } from '@/entities/capability/model/types';

export const stagingCapabilitiesFixture: AnalysisCapabilities = {
  snapshotId: 'gold-v5',
  datasetId: 'finance-vietnam-banks',
  datasetSnapshotId: 'gold-v5',
  dataset_snapshot_id: 'gold-v5',
  goldVersion: 'v5',
  entities: [
    { id: 'ACB', ticker: 'ACB', name: 'ACB', type: 'company' },
    { id: 'TCB', ticker: 'TCB', name: 'TCB', type: 'company' },
    { id: 'VPB', ticker: 'VPB', name: 'VPB', type: 'company' },
    { id: 'MBB', ticker: 'MBB', name: 'MBB', type: 'company' },
    { id: 'VCB', ticker: 'VCB', name: 'VCB', type: 'company' }
  ],
  periods: [
    { id: '2024_Q1', label: 'Q1 2024', year: 2024, quarter: 1 },
    { id: '2024_Q2', label: 'Q2 2024', year: 2024, quarter: 2 },
    { id: '2024_Q3', label: 'Q3 2024', year: 2024, quarter: 3 },
    { id: '2024_Q4', label: 'Q4 2024', year: 2024, quarter: 4 }
  ],
  metrics: [
    {
      id: 'bank.npl_g35',
      acronym: 'NPL_G35',
      label: 'Tỷ lệ nợ xấu (nhóm 3–5)',
      shortLabel: 'Nợ xấu',
      topicId: 'company',
      unit: '%',
      direction: 'lower_is_better',
      decimals: 2,
      group: 'asset_quality',
      groupLabel: 'Chất lượng nợ'
    },
    {
      id: 'bank.llr_coverage',
      acronym: 'LLR_COVERAGE',
      label: 'Tỷ lệ bao phủ nợ xấu',
      shortLabel: 'Bao phủ nợ xấu',
      topicId: 'company',
      unit: '%',
      direction: 'higher_is_better',
      decimals: 2,
      group: 'asset_quality',
      groupLabel: 'Chất lượng nợ'
    },
    {
      id: 'bank.roa',
      acronym: 'ROA',
      label: 'Tỷ suất sinh lời trên tổng tài sản',
      shortLabel: 'ROA',
      topicId: 'company',
      unit: '%',
      direction: 'higher_is_better',
      decimals: 2,
      group: 'profitability',
      groupLabel: 'Khả năng sinh lời'
    },
    {
      id: 'bank.roe',
      acronym: 'ROE',
      label: 'Tỷ suất sinh lời trên vốn chủ sở hữu',
      shortLabel: 'ROE',
      topicId: 'company',
      unit: '%',
      direction: 'higher_is_better',
      decimals: 2,
      group: 'profitability',
      groupLabel: 'Khả năng sinh lời'
    }
  ],
  topics: [],
  peerUniverse: {
    id: 'peer-bank-5',
    label: 'Snapshot peer group (5 companies)',
    entityIds: ['ACB', 'TCB', 'VPB', 'MBB', 'VCB'],
    readonly: true,
    executable: true,
    description: 'Nhóm 5 ngân hàng niêm yết được kiểm định trong snapshot Gold.'
  },
  peerUniverses: [
    {
      id: 'peer-bank-5',
      label: 'Snapshot peer group (5 companies)',
      entityIds: ['ACB', 'TCB', 'VPB', 'MBB', 'VCB'],
      readonly: true,
      executable: true,
      description: 'Nhóm 5 ngân hàng niêm yết được kiểm định trong snapshot Gold.'
    }
  ],
  macro: {
    status: 'UNAVAILABLE',
    minimumContractSatisfied: false,
    summary: 'No accepted macro observation capability is declared.',
    details: 'The API analysis route requires declared macro observations before macro claims can execute.',
    executable: false
  },
  database_status: 'connected',
  analysis_available: true,
  implemented_capabilities: ['company', 'sector'],
  supported_operations: ['get_company_metric', 'get_peer_benchmark'],
  source: 'gold-sqlite',
  readiness: 'Runnable for company claims.',
  coverage: ['ACB', 'TCB', 'VPB', 'MBB', 'VCB'].flatMap((entityId) =>
    ['2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4'].map((periodId) => ({
      entity_id: entityId,
      period_id: periodId,
      metrics: ['bank.npl_g35', 'bank.llr_coverage', 'bank.roa', 'bank.roe'],
    }))
  ),
};
