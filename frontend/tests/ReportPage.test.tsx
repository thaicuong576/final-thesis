import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { ReportPage } from '../src/pages/reports/ReportPage';
import { ReportsListPage } from '../src/pages/reports/ReportsListPage';
import { CompanyCamelBreakdown, EvidenceTrailTable, SectorBenchmarkMatrix, type AnalysisReport } from '../src/features/analysis-report';

const partialReport: AnalysisReport = {
  report_id: 'rep-live-42',
  status: 'partial',
  query: 'Phân tích ROE của ACB tại Q4/2024',
  target_ticker: 'ACB',
  period: '2024_Q4',
  atomic_claims: [{
    claim_id: 'claim-1',
    capability: 'company',
    statement: 'API returned an observation.',
    claim_type: 'factual_observation',
    evidence_refs: ['ev-linkable', 'ev-unlinked'],
    confidence: 0.7,
    stage1_status: 'accepted',
    stage2_critique_status: null
  }],
  evidence_trail: [
    {
      evidence_id: 'ev-linkable',
      metric: 'ROE', ticker: 'ACB', period: '2024_Q4', value: 10,
      source_doc: 'https://example.test/source.pdf', table_locator: 'page 12'
    },
    {
      evidence_id: 'ev-unlinked',
      metric: 'ROE', ticker: 'ACB', period: '2024_Q4', value: null,
      source_doc: null, table_locator: null, provenance_hash: null
    }
  ]
};

function renderReport(path: string, report?: AnalysisReport) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes><Route path="/reports/:id" element={<ReportPage report={report} />} /></Routes>
    </MemoryRouter>
  );
}

describe('Analysis report truth and provenance', () => {
  it('marks the routed sample report as simulated content', () => {
    renderReport('/reports/acb-solo');

    expect(screen.getByText(/Mẫu minh họa, dữ liệu giả lập/)).toBeInTheDocument();
    expect(screen.getByText('Mẫu minh họa')).toBeInTheDocument();
    expect(screen.queryByText('Kiểm định đối soát BCTC độc lập')).not.toBeInTheDocument();
  });

  it('keeps a composite API report readable when its plan rationale is unknown', () => {
    renderReport('/reports/rep-live-42', {
      ...partialReport,
      analysis_plan: {
        plan_id: 'plan-live-42',
        query: partialReport.query!,
        target_ticker: 'ACB',
        peer_tickers: [],
        period: null,
        required_capabilities: ['company'],
        applicable_links: [],
        dataset_snapshot_id: 'snapshot-live-42',
        rationale: null,
        known_limitations: []
      }
    });

    expect(screen.getByText('API không công bố lý do lập kế hoạch cho báo cáo này.')).toBeInTheDocument();
  });

  it('labels a partial live response and leaves Stage 2 unknown when the API omits it', () => {
    renderReport('/reports/rep-live-42', partialReport);

    expect(screen.getByText('Kết quả phân tích chưa hoàn tất.')).toBeInTheDocument();
    expect(screen.getByText('Trạng thái API: Kết quả một phần')).toBeInTheDocument();
    expect(screen.getByText('Phản biện: chưa công bố')).toBeInTheDocument();
    expect(screen.queryByText('Kiểm tra số học: Đạt')).not.toBeInTheDocument();
    expect(screen.queryByText('Phản biện logic: Đạt')).not.toBeInTheDocument();
    expect(screen.queryByText(/Mẫu minh họa, dữ liệu giả lập/)).not.toBeInTheDocument();
  });

  it('links evidence only when its source URL and locator are present', () => {
    renderReport('/reports/rep-live-42', partialReport);

    expect(screen.getByRole('link', { name: 'https://example.test/source.pdf' })).toHaveAttribute('href', 'https://example.test/source.pdf');
    expect(screen.getByRole('button', { name: '#ev-linkable' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '#ev-unlinked' })).not.toBeInTheDocument();
    expect(screen.getByText('#ev-unlinked')).toBeInTheDocument();
  });

  it('does not link a valid source URL when its locator is missing', () => {
    const sourceUrl = 'https://example.test/missing-locator.pdf';
    render(<EvidenceTrailTable evidenceTrail={[{
      evidence_id: 'ev-no-locator',
      metric: 'ROE',
      ticker: 'ACB',
      period: '2024_Q4',
      value: 10,
      source_url: sourceUrl,
      table_locator: '  '
    }]} />);

    expect(screen.getByText(sourceUrl)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: sourceUrl })).not.toBeInTheDocument();
  });

  it('renders only returned benchmark and company metric values', () => {
    const { rerender } = render(
      <SectorBenchmarkMatrix sectorBenchmark={{
        sector: 'provider peer group',
        peer_median_roe: null,
        peer_median_nim: 2.5,
        peer_median_npl: null,
        peer_median_cir: null,
        peer_median_casa: null,
        peer_median_car: null,
        peer_median_ldr: null
      }} period="2024_Q4" />
    );
    expect(screen.getByText('2.50%')).toBeInTheDocument();
    expect(screen.getAllByText('— (thiếu)').length).toBeGreaterThan(0);

    rerender(<CompanyCamelBreakdown
      companyInsights={[{
        ticker: 'ABC', roe: 10, nim: null, npl: null, cir: null, casa: null, car: null, ldr: null,
        assessment: ''
      }]}
      targetTicker="ABC"
    />);
    expect(screen.getByText('10.00%')).toBeInTheDocument();
    expect(screen.queryByText(/đạt tỷ suất ROE|vượt trội về NIM/i)).not.toBeInTheDocument();
  });

  it('labels the report library as simulated examples rather than API results', () => {
    render(<MemoryRouter initialEntries={['/reports']}><Routes><Route path="/reports" element={<ReportsListPage />} /></Routes></MemoryRouter>);
    expect(screen.getByText('3 MẪU MINH HỌA · KHÔNG PHẢI KẾT QUẢ API')).toBeInTheDocument();
    expect(screen.getByText(/không phải kết quả đã kiểm định/)).toBeInTheDocument();
    expect(screen.getAllByText('Mẫu minh họa').length).toBeGreaterThan(0);
  });
});
