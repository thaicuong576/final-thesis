import type { AnalysisReport } from '../model/types';

export const mockPeerComparisonReport: AnalysisReport = {
  session_id: 'mock-session-peer-acb-tcb',
  report_id: 'rep-2024-acb-tcb-peer',
  status: 'completed',
  query: 'So sánh hiệu quả hoạt động (ROE, NIM) và rủi ro nợ xấu (NPL) giữa ACB và TCB năm 2024',
  target_ticker: 'ACB',
  peer_tickers: ['TCB', 'MBB'],
  period: '2024',
  analysis_plan: {
    plan_id: 'plan-peer-acb-tcb-2024',
    query: 'So sánh hiệu quả hoạt động (ROE, NIM) và rủi ro nợ xấu (NPL) giữa ACB và TCB năm 2024',
    target_ticker: 'ACB',
    peer_tickers: ['TCB', 'MBB'],
    period: '2024',
    required_capabilities: ['company', 'sector'],
    applicable_links: ['peer_comparison'],
    dataset_snapshot_id: 'snap-2024-q4-v1',
    rationale: 'Yêu cầu so sánh hiệu quả và chất lượng tài sản giữa ngân hàng mục tiêu và nhóm đối thủ, kích hoạt Doanh nghiệp và Đối chuẩn ngành.',
    known_limitations: []
  },
  macro_context: {
    sbv_policy_rate: 4.5,
    system_credit_growth: 15.08,
    interest_rate_trend: 'Chính sách tiền tệ nới lỏng thận trọng của NHNN hỗ trợ phục hồi tín dụng khu vực tư nhân và giảm áp lực chi phí vốn.',
    source: 'Định hướng điều hành NHNN 2024 (SBV Annual Direction 2024)'
  },
  sector_benchmark: {
    sector: 'Ngành Ngân hàng niêm yết (Banking)',
    peer_median_roe: 18.2,
    peer_median_nim: 3.65,
    peer_median_npl: 1.62,
    peer_median_cir: 33.4,
    peer_median_casa: 28.5,
    peer_median_car: 11.8,
    peer_median_ldr: 78.4
  },
  company_insights: [
    {
      ticker: 'ACB',
      roe: 21.4,
      nim: 3.82,
      npl: 1.21,
      cir: 31.8,
      casa: 23.2,
      car: 12.8,
      ldr: 82.5,
      assessment: 'ACB đạt tỷ suất ROE 21.4% cao hơn trung vị ngành (18.2%) nhờ tối ưu hóa chi phí (CIR 31.8%) và kiểm soát rủi ro tín dụng chặt chẽ (NPL 1.21%).'
    },
    {
      ticker: 'TCB',
      roe: 17.8,
      nim: 4.15,
      npl: 1.45,
      cir: 32.5,
      casa: 41.2,
      car: 14.5,
      ldr: 77.2,
      assessment: 'TCB vượt trội về NIM (4.15% vs 3.65% trung vị) nhờ tỷ lệ CASA dẫn đầu ngành 41.2% và đệm vốn CAR 14.5% vững chắc.'
    }
  ],
  cross_level_critique: [
    {
      dimension: 'Đánh đổi ROE và Chi phí Hoạt động (ROE vs CIR Trade-off)',
      finding: 'ACB đạt ROE cao hơn TCB (21.4% vs 17.8%) nhờ chi phí dự phòng rủi ro tín dụng thấp hơn và CIR tối ưu hơn (31.8% vs 32.5%).',
      confidence: 0.94,
      evidence_ref: 'ACB-FY24-AR-p42'
    },
    {
      dimension: 'Biên Lãi Thuần & Giá Vốn Huy Động (NIM & Cost of Funds)',
      finding: 'TCB có NIM cao hơn ACB (4.15% vs 3.82%) chủ yếu nhờ tỷ lệ CASA 41.2% giúp hạ giá vốn huy động.',
      confidence: 0.95,
      evidence_ref: 'TCB-FY24-AR-p58'
    }
  ],
  atomic_claims: [
    {
      claim_id: 'claim-acb-roe-peer',
      capability: 'company',
      ticker: 'ACB',
      metric: 'ROE',
      period: '2024',
      statement: 'ROE của ACB năm 2024 đạt 21.4%, vượt trung vị ngành ngân hàng 3.2 điểm %.',
      claim_type: 'peer_comparison',
      evidence_refs: ['ev-acb-roe-2024', 'ev-median-roe-2024'],
      confidence: 0.98,
      stage1_status: 'accepted',
      stage2_critique_status: 'sound'
    },
    {
      claim_id: 'claim-tcb-nim-peer',
      capability: 'company',
      ticker: 'TCB',
      metric: 'NIM',
      period: '2024',
      statement: 'NIM của TCB năm 2024 đạt 4.15%, vượt 50 bps so với trung vị nhóm ngân hàng đối chuẩn (3.65%).',
      claim_type: 'peer_comparison',
      evidence_refs: ['ev-tcb-nim-2024', 'ev-median-nim-2024'],
      confidence: 0.97,
      stage1_status: 'accepted',
      stage2_critique_status: 'sound'
    }
  ],
  evidence_trail: [
    {
      evidence_id: 'ev-acb-roe-2024',
      metric: 'ROE',
      ticker: 'ACB',
      period: '2024',
      value: 21.4,
      source_doc: 'Báo cáo tài chính kiểm toán hợp nhất 2024 - ACB',
      table_locator: 'Báo cáo kết quả hoạt động kinh doanh',
      provenance_hash: 'hash-acb-pl-2024'
    },
    {
      evidence_id: 'ev-tcb-nim-2024',
      metric: 'NIM',
      ticker: 'TCB',
      period: '2024',
      value: 4.15,
      source_doc: 'Báo cáo thường niên 2024 - TCB',
      table_locator: 'Bảng tổng hợp chỉ tiêu tài chính chủ yếu',
      provenance_hash: 'hash-tcb-nim-2024'
    },
    {
      evidence_id: 'ev-median-roe-2024',
      metric: 'peer_median_roe',
      ticker: 'SECTOR',
      period: '2024',
      value: 18.2,
      source_doc: 'Tổng hợp chỉ số ngành ngân hàng niêm yết 2024',
      table_locator: 'Ma trận đối chuẩn ngành',
      provenance_hash: 'hash-sector-median-2024'
    },
    {
      evidence_id: 'ev-median-nim-2024',
      metric: 'peer_median_nim',
      ticker: 'SECTOR',
      period: '2024',
      value: 3.65,
      source_doc: 'Tổng hợp chỉ số ngành ngân hàng niêm yết 2024',
      table_locator: 'Ma trận đối chuẩn ngành',
      provenance_hash: 'hash-sector-median-2024'
    }
  ],
  revision_summary: {
    rounds_executed: 0,
    max_rounds: 2,
    status: 'passed',
    reason: 'Hoàn thành thẩm định Stage 1 và Stage 2 không phát hiện mâu thuẫn đối chuẩn.',
    revised_capabilities: []
  },
  limitations: []
};

export const mockCompanyOnlyReport: AnalysisReport = {
  session_id: 'mock-session-company-acb',
  report_id: 'rep-2024-acb-solo',
  status: 'completed',
  query: 'Phân tích sức khỏe tài chính và các chỉ tiêu CAMEL của ACB năm 2024',
  target_ticker: 'ACB',
  peer_tickers: [],
  period: '2024',
  analysis_plan: {
    plan_id: 'plan-company-acb-2024',
    query: 'Phân tích sức khỏe tài chính và các chỉ tiêu CAMEL của ACB năm 2024',
    target_ticker: 'ACB',
    peer_tickers: [],
    period: '2024',
    required_capabilities: ['company'],
    applicable_links: [],
    dataset_snapshot_id: 'snap-2024-q4-v1',
    rationale: 'Yêu cầu phân tích độc lập ACB theo 5 trụ cột CAMEL, không kích hoạt đối chuẩn ngành hay vĩ mô.',
    known_limitations: [
      'Không đối sánh với trung vị ngành vì yêu cầu phân tích độc lập ngân hàng mục tiêu.'
    ]
  },
  macro_context: null,
  sector_benchmark: null,
  company_insights: [
    {
      ticker: 'ACB',
      roe: 21.4,
      nim: 3.82,
      npl: 1.21,
      cir: 31.8,
      casa: 23.2,
      car: 12.8,
      ldr: 82.5,
      assessment: 'Chất lượng tài sản ACB duy trì vượt trội với tỷ lệ nợ xấu 1.21%. Hiệu quả sinh lời vốn chủ sở hữu (ROE 21.4%) và đệm an toàn vốn (CAR 12.8%) vững chắc nhờ chiến lược bán lẻ thận trọng.'
    }
  ],
  cross_level_critique: [],
  atomic_claims: [
    {
      claim_id: 'claim-acb-roe-solo',
      capability: 'company',
      ticker: 'ACB',
      metric: 'ROE',
      period: '2024',
      statement: 'ROE của ACB năm 2024 đạt 21.4%, phản ánh khả năng sinh lời trên vốn chủ sở hữu cao và ổn định.',
      claim_type: 'factual_observation',
      evidence_refs: ['ev-acb-roe-2024'],
      confidence: 0.99,
      stage1_status: 'accepted',
      stage2_critique_status: 'sound'
    },
    {
      claim_id: 'claim-acb-npl-solo',
      capability: 'company',
      ticker: 'ACB',
      metric: 'NPL',
      period: '2024',
      statement: 'Tỷ lệ nợ xấu của ACB tại thời điểm kết thúc năm tài chính 2024 là 1.21%, kiểm soát tốt trong ngưỡng an toàn.',
      claim_type: 'factual_observation',
      evidence_refs: ['ev-acb-npl-2024'],
      confidence: 0.99,
      stage1_status: 'accepted',
      stage2_critique_status: 'sound'
    }
  ],
  evidence_trail: [
    {
      evidence_id: 'ev-acb-roe-2024',
      metric: 'ROE',
      ticker: 'ACB',
      period: '2024',
      value: 21.4,
      source_doc: 'Báo cáo tài chính kiểm toán hợp nhất 2024 - ACB',
      table_locator: 'Báo cáo kết quả hoạt động kinh doanh',
      provenance_hash: 'hash-acb-pl-2024'
    },
    {
      evidence_id: 'ev-acb-npl-2024',
      metric: 'NPL',
      ticker: 'ACB',
      period: '2024',
      value: 1.21,
      source_doc: 'Báo cáo tài chính kiểm toán hợp nhất 2024 - ACB',
      table_locator: 'Thuyết minh cho vay khách hàng theo nhóm nợ',
      provenance_hash: 'hash-acb-loan-2024'
    }
  ],
  revision_summary: {
    rounds_executed: 0,
    max_rounds: 2,
    status: 'passed',
    reason: 'Các khẳng định số học đạt chuẩn Stage 1 và được phê chuẩn tại vòng thẩm định đầu tiên.',
    revised_capabilities: []
  },
  limitations: [
    'Báo cáo không bao gồm đối chuẩn trung vị ngành do phạm vi yêu cầu chỉ phân tích nội tại ACB.'
  ]
};

export function getReportById(id?: string | null): AnalysisReport {
  if (!id) return mockPeerComparisonReport;
  const lower = id.toLowerCase();
  if (lower.includes('company') || lower.includes('solo') || lower === 'scenario_company_only' || lower === 'rep-2024-acb-solo') {
    return mockCompanyOnlyReport;
  }
  return mockPeerComparisonReport;
}
