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
    source: 'Định hướng điều hành NHNN 2024'
  },
  sector_benchmark: {
    sector: 'Ngành Ngân hàng niêm yết',
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
      dimension: 'Đánh đổi ROE và Chi phí Hoạt động',
      finding: 'ACB đạt ROE cao hơn TCB (21.4% vs 17.8%) nhờ chi phí dự phòng rủi ro tín dụng thấp hơn và CIR tối ưu hơn (31.8% vs 32.5%).',
      confidence: 0.94,
      evidence_ref: 'ACB-FY24-AR-p42'
    },
    {
      dimension: 'Biên Lãi Thuần và Giá Vốn Huy Động',
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
    reason: 'Hoàn thành thẩm định kiểm tra số học và phản biện logic không phát hiện mâu thuẫn đối chuẩn.',
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
    rationale: 'Yêu cầu phân tích độc lập ACB theo 5 trụ cột sức khỏe tài chính, không kích hoạt đối chuẩn ngành hay vĩ mô.',
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
    reason: 'Các khẳng định số học đạt chuẩn kiểm định và được phê chuẩn tại vòng thẩm định đầu tiên.',
    revised_capabilities: []
  },
  limitations: [
    'Báo cáo không bao gồm đối chuẩn trung vị ngành do phạm vi yêu cầu chỉ phân tích nội tại ACB.'
  ]
};

export const mockFullHierarchicalReport: AnalysisReport = {
  session_id: 'mock-session-full-hierarchical',
  report_id: 'rep-2024-full-macro-sector-camel',
  status: 'completed',
  query: 'Đánh giá toàn diện tác động chính sách tiền tệ NHNN đến NIM và nợ xấu (NPL) của ACB và TCB năm 2024',
  target_ticker: 'ACB',
  peer_tickers: ['TCB', 'MBB'],
  period: '2024',
  analysis_plan: {
    plan_id: 'plan-full-hierarchical-2024',
    query: 'Đánh giá toàn diện tác động chính sách tiền tệ NHNN đến NIM và nợ xấu (NPL) của ACB và TCB năm 2024',
    target_ticker: 'ACB',
    peer_tickers: ['TCB', 'MBB'],
    period: '2024',
    required_capabilities: ['macro', 'sector', 'company'],
    applicable_links: ['macro_transmission', 'peer_comparison', 'cross_level_stress'],
    dataset_snapshot_id: 'snap-2024-q4-v1',
    rationale: 'Yêu cầu phân tích tác động xuyên tầng từ chính sách vĩ mô sang trung vị ngành và từng ngân hàng, kích hoạt đầy đủ 3 năng lực phân tích.',
    known_limitations: []
  },
  macro_context: {
    sbv_policy_rate: 4.5,
    system_credit_growth: 15.08,
    interest_rate_trend: 'Chính sách tiền tệ nới lỏng thận trọng của NHNN hỗ trợ phục hồi tín dụng khu vực tư nhân và giảm áp lực chi phí vốn.',
    source: 'Định hướng điều hành NHNN 2024'
  },
  sector_benchmark: {
    sector: 'Ngành Ngân hàng niêm yết',
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
      assessment: 'ACB duy trì chất lượng tài sản an toàn cao (NPL 1.21%) và NIM phục hồi lên 3.82% nhờ cơ cấu danh mục cho vay thận trọng thích ứng tốt với chính sách tiền tệ nới lỏng.'
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
      assessment: 'TCB hưởng lợi lớn từ mặt bằng lãi suất thấp thông qua tỷ lệ CASA 41.2%, giúp NIM đạt 4.15% dẫn đầu phân khúc ngân hàng thương mại cổ phần tư nhân.'
    }
  ],
  cross_level_critique: [
    {
      dimension: 'Truyền dẫn lãi suất vĩ mô sang NIM',
      finding: 'Chính sách nới lỏng của NHNN hỗ trợ giảm chi phí vốn nhanh hơn lãi suất cho vay, tạo điều kiện mở rộng NIM tại TCB (4.15%) và bảo toàn NIM tại ACB (3.82%).',
      confidence: 0.94,
      evidence_ref: 'SBV-Dir24-p12'
    },
    {
      dimension: 'Tăng trưởng tín dụng và chất lượng tài sản',
      finding: 'Tăng trưởng tín dụng toàn hệ thống đạt 15.08% gây áp lực nợ xấu tăng ở phân khúc tiêu dùng, tuy nhiên tỷ lệ nợ xấu của ACB (1.21%) vẫn thấp hơn trung vị toàn ngành (1.62%).',
      confidence: 0.95,
      evidence_ref: 'ACB-FY24-AR-p42'
    }
  ],
  atomic_claims: [
    {
      claim_id: 'claim-macro-sbv-rate',
      capability: 'macro',
      ticker: null,
      metric: 'sbv_policy_rate',
      period: '2024',
      statement: 'Lãi suất tái cấp vốn của NHNN giữ ở mức 4.5% trong năm 2024 nhằm hỗ trợ phục hồi tăng trưởng kinh tế.',
      claim_type: 'policy_transmission',
      evidence_refs: ['ev-sbv-rate-2024'],
      confidence: 0.99,
      stage1_status: 'accepted',
      stage2_critique_status: 'sound'
    },
    {
      claim_id: 'claim-cross-nim-trans',
      capability: 'synthesis',
      ticker: 'TCB',
      metric: 'NIM',
      period: '2024',
      statement: 'Tác động truyền dẫn từ lãi suất điều hành thấp giúp TCB duy trì NIM 4.15% nhờ tỷ trọng tiền gửi không kỳ hạn CASA 41.2%.',
      claim_type: 'synthesis_evaluation',
      evidence_refs: ['ev-sbv-rate-2024', 'ev-tcb-casa-2024', 'ev-tcb-nim-2024'],
      confidence: 0.95,
      stage1_status: 'accepted',
      stage2_critique_status: 'revised'
    },
    {
      claim_id: 'claim-acb-npl-stress',
      capability: 'company',
      ticker: 'ACB',
      metric: 'NPL',
      period: '2024',
      statement: 'Tỷ lệ nợ xấu của ACB năm 2024 là 1.21%, duy trì đệm an toàn cao hơn trung vị ngành (1.62%) trước áp lực nợ xấu chu kỳ.',
      claim_type: 'peer_comparison',
      evidence_refs: ['ev-acb-npl-2024', 'ev-median-npl-2024'],
      confidence: 0.97,
      stage1_status: 'accepted',
      stage2_critique_status: 'sound'
    }
  ],
  evidence_trail: [
    {
      evidence_id: 'ev-sbv-rate-2024',
      metric: 'sbv_policy_rate',
      ticker: 'MACRO',
      period: '2024',
      value: 4.5,
      source_doc: 'Quyết định điều hành lãi suất NHNN 2024',
      table_locator: 'Điều 1',
      provenance_hash: 'hash-sbv-rate-2024'
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
    },
    {
      evidence_id: 'ev-tcb-casa-2024',
      metric: 'CASA',
      ticker: 'TCB',
      period: '2024',
      value: 41.2,
      source_doc: 'Báo cáo tài chính kiểm toán hợp nhất 2024 - TCB',
      table_locator: 'Thuyết minh tiền gửi của khách hàng',
      provenance_hash: 'hash-tcb-dep-2024'
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
      evidence_id: 'ev-median-npl-2024',
      metric: 'peer_median_npl',
      ticker: 'SECTOR',
      period: '2024',
      value: 1.62,
      source_doc: 'Tổng hợp chỉ số ngành ngân hàng niêm yết 2024',
      table_locator: 'Ma trận đối chuẩn ngành',
      provenance_hash: 'hash-sector-median-2024'
    }
  ],
  revision_summary: {
    rounds_executed: 1,
    max_rounds: 2,
    status: 'revised_and_passed',
    reason: 'Hiệu đính nhận định về độ trễ truyền dẫn chi phí vốn sang NIM sau khi đối chiếu thuyết minh chi phí lãi quý 4.',
    revised_capabilities: ['company']
  },
  limitations: []
};

export interface SampleReportItem {
  id: string;
  slug: string;
  name: string;
  shortName: string;
  query: string;
  targetTicker: string;
  peerTickers: string[];
  period: string;
  scopeBadge: string;
  capabilities: string[];
  statusLabel: string;
  hasRevision: boolean;
  date: string;
  report: AnalysisReport;
}

export const SAMPLE_REPORTS: SampleReportItem[] = [
  {
    id: 'acb-solo',
    slug: 'acb-solo',
    name: 'Mẫu 1: ACB độc lập',
    shortName: 'Mẫu 1: ACB',
    query: 'Phân tích sức khỏe tài chính và các chỉ tiêu CAMEL của ACB năm 2024',
    targetTicker: 'ACB',
    peerTickers: [],
    period: '2024',
    scopeBadge: 'ACB · Độc lập · 2024',
    capabilities: ['Doanh nghiệp (5 trụ cột)'],
    statusLabel: 'Hoàn tất',
    hasRevision: false,
    date: '15/09/2026',
    report: mockCompanyOnlyReport
  },
  {
    id: 'acb-tcb-peer',
    slug: 'acb-tcb-peer',
    name: 'Mẫu 2: ACB vs TCB',
    shortName: 'Mẫu 2: ACB vs TCB',
    query: 'So sánh hiệu quả hoạt động (ROE, NIM) và rủi ro nợ xấu (NPL) giữa ACB và TCB năm 2024',
    targetTicker: 'ACB',
    peerTickers: ['TCB', 'MBB'],
    period: '2024',
    scopeBadge: 'ACB · TCB · MBB · 2024',
    capabilities: ['Doanh nghiệp & Đối chuẩn ngành'],
    statusLabel: 'Hoàn tất',
    hasRevision: false,
    date: '18/09/2026',
    report: mockPeerComparisonReport
  },
  {
    id: 'full-hierarchical',
    slug: 'full-hierarchical',
    name: 'Mẫu 3: Đa tầng Vĩ mô kèm hiệu đính',
    shortName: 'Mẫu 3: Đa tầng Vĩ mô',
    query: 'Đánh giá toàn diện tác động chính sách tiền tệ NHNN đến NIM và nợ xấu (NPL) của ACB và TCB năm 2024',
    targetTicker: 'ACB',
    peerTickers: ['TCB', 'MBB'],
    period: '2024',
    scopeBadge: 'ACB · TCB · Vĩ mô NHNN · 2024',
    capabilities: ['Vĩ mô, Ngành & Doanh nghiệp'],
    statusLabel: 'Đã hiệu đính',
    hasRevision: true,
    date: '20/09/2026',
    report: mockFullHierarchicalReport
  }
];

export function getReportById(id?: string | null): AnalysisReport | null {
  if (!id) return null;
  return SAMPLE_REPORTS.find((sample) => sample.slug === id || sample.id === id)?.report ?? null;
}
