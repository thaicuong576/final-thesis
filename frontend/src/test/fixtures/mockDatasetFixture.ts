export const mockAnalysisDatasetFixture = {
  summary: {
    name: 'Ngân hàng Việt Nam 2024',
    readiness: 'READY',
    entityCount: 5,
    periodLabel: 'Q1–Q4/2024',
    metricCount: 4,
    documentCount: 17,
    scope: {
      entities: 'Đã xác định',
      peerUniverse: 'Đã xác định',
      macro: 'LIMITED'
    }
  },
  entities: ['ACB', 'TCB', 'MBB', 'VCB', 'VPB'],
  periods: ['Q1', 'Q2', 'Q3', 'Q4'],
  metrics: ['NPL', 'Coverage', 'ROA', 'ROE'],
  sources: [
    {
      id: 'bank-financials',
      kind: 'structured',
      title: 'Dữ liệu tài chính ngân hàng',
      typeLabel: 'Bảng dữ liệu',
      statusLabel: 'Đã xác thực',
      observationCount: 80,
      validObservationCount: 76,
      missingValueCount: 4,
      duplicateCount: 0,
      updatedAt: '11/09/2026'
    },
    {
      id: 'source-documents',
      kind: 'documents',
      title: 'Báo cáo & tài liệu nguồn',
      typeLabel: 'Tài liệu',
      statusLabel: 'Đã lập chỉ mục',
      documentCount: 17,
      examples: ['Báo cáo thường niên', 'Báo cáo quý', 'Văn bản chính sách / quy định'],
      updatedAt: '11/09/2026'
    }
  ]
};
