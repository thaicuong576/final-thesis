import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MarketPriceStrip } from '../src/features/market-context/MarketPriceStrip';
import { ReportMarketRow } from '../src/features/market-context/ReportMarketRow';
import { ValuationScatterChart } from '../src/features/market-context/ValuationScatterChart';
import { WorkspaceShell } from '../src/components/layout/WorkspaceShell';
import { AnalysisSessionWorkspace } from '../src/features/analysis-session/components/AnalysisSessionWorkspace';
import { AdaptiveReport } from '../src/features/equity-report';
import type { AdaptiveReportResponse } from '../src/features/equity-report/model/types';
import {
  formatReadingMethod,
  buildAuditVerdictPresentation,
  findLeafSourceMetadata,
  buildInputStepDetail
} from '../src/features/source-lineage/readingWording';
import type { MarketQuotesResponse, MarketValuationResponse } from '../src/features/market-context/types';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false
      }
    }
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

const mockQuotesConfigured: MarketQuotesResponse = {
  configured: true,
  source: 'SSI FastConnect Data',
  fetched_at: '2026-10-12T14:30:00+07:00',
  stale: false,
  quotes: [
    { ticker: 'ACB', close: 25400, reference: 25000, change: 400, change_percent: 1.6, volume: 5000000, trading_date: '12/10/2026', fetched_at: '2026-10-12T14:30:00+07:00', source: 'SSI FastConnect Data', stale: false },
    { ticker: 'BID', close: 48200, reference: 48500, change: -300, change_percent: -0.62, volume: 2000000, trading_date: '12/10/2026', fetched_at: '2026-10-12T14:30:00+07:00', source: 'SSI FastConnect Data', stale: false },
    { ticker: 'CTG', close: 35100, reference: 35100, change: 0, change_percent: 0, volume: 3000000, trading_date: '12/10/2026', fetched_at: '2026-10-12T14:30:00+07:00', source: 'SSI FastConnect Data', stale: false },
    { ticker: 'HDB', close: 26800, reference: 26500, change: 300, change_percent: 1.13, volume: 1500000, trading_date: '12/10/2026', fetched_at: '2026-10-12T14:30:00+07:00', source: 'SSI FastConnect Data', stale: false },
    { ticker: 'MBB', close: 24200, reference: 24000, change: 200, change_percent: 0.83, volume: 4000000, trading_date: '12/10/2026', fetched_at: '2026-10-12T14:30:00+07:00', source: 'SSI FastConnect Data', stale: false },
    { ticker: 'SHB', close: 10800, reference: 10900, change: -100, change_percent: -0.92, volume: 6000000, trading_date: '12/10/2026', fetched_at: '2026-10-12T14:30:00+07:00', source: 'SSI FastConnect Data', stale: false },
    { ticker: 'STB', close: 31500, reference: 31000, change: 500, change_percent: 1.61, volume: 3500000, trading_date: '12/10/2026', fetched_at: '2026-10-12T14:30:00+07:00', source: 'SSI FastConnect Data', stale: false },
    { ticker: 'TCB', close: 23600, reference: 23400, change: 200, change_percent: 0.85, volume: 4500000, trading_date: '12/10/2026', fetched_at: '2026-10-12T14:30:00+07:00', source: 'SSI FastConnect Data', stale: false },
    { ticker: 'VCB', close: 91800, reference: 91500, change: 300, change_percent: 0.33, volume: 1200000, trading_date: '12/10/2026', fetched_at: '2026-10-12T14:30:00+07:00', source: 'SSI FastConnect Data', stale: false },
    { ticker: 'VPB', close: 19100, reference: 19300, change: -200, change_percent: -1.04, volume: 5500000, trading_date: '12/10/2026', fetched_at: '2026-10-12T14:30:00+07:00', source: 'SSI FastConnect Data', stale: false }
  ]
};

const mockQuotesStale: MarketQuotesResponse = {
  ...mockQuotesConfigured,
  stale: true,
  stale_reason: 'Phien giao dich truoc hoac ngoai gio'
};

const mockQuotesUnconfigured: MarketQuotesResponse = {
  configured: false,
  source: 'SSI FastConnect Data',
  stale: false,
  quotes: []
};

const mockValuationConfigured: MarketValuationResponse = {
  configured: true,
  source: 'SSI FastConnect Data',
  fetched_at: '2026-10-12T14:30:00+07:00',
  stale: false,
  items: [
    {
      ticker: 'VCB',
      close: 91800,
      pb: 1.91,
      roe: 19.5,
      inputs: {
        close_vnd: 91800,
        close_source: 'SSI FastConnect Data',
        close_date: '12/10/2026',
        listed_shares: 5589000000,
        shares_source: 'SSI FastConnect Data (SecuritiesDetails)',
        parent_attributable_equity_billion_vnd: 268000,
        equity_period: '2024_Q4',
        equity_source: 'BCTC Hợp nhất Q4/2024 VCB',
        roe_percent: 19.5,
        roe_period: '2024_Q4',
        formula: 'P/B = close_vnd / (parent_attributable_equity_billion_vnd * 1e9 / listed_shares)'
      }
    },
    {
      ticker: 'ACB',
      close: 25400,
      pb: 1.35,
      roe: 21.0,
      inputs: {
        close_vnd: 25400,
        close_source: 'SSI FastConnect Data',
        close_date: '12/10/2026',
        listed_shares: 4466000000,
        shares_source: 'SSI FastConnect Data (SecuritiesDetails)',
        parent_attributable_equity_billion_vnd: 84000,
        equity_period: '2024_Q4',
        equity_source: 'BCTC Hợp nhất Q4/2024 ACB',
        roe_percent: 21.0,
        roe_period: '2024_Q4',
        formula: 'P/B = close_vnd / (parent_attributable_equity_billion_vnd * 1e9 / listed_shares)'
      }
    },
    {
      ticker: 'STB',
      close: 31500,
      pb: 1.10,
      roe: 10.2, // > 8 points below median of ~19.5%
      inputs: {
        close_vnd: 31500,
        close_source: 'SSI FastConnect Data',
        close_date: '12/10/2026',
        listed_shares: 1885000000,
        shares_source: 'SSI FastConnect Data (SecuritiesDetails)',
        parent_attributable_equity_billion_vnd: 54000,
        equity_period: '2024_Q4',
        equity_source: 'BCTC Hợp nhất Q4/2024 STB',
        roe_percent: 10.2,
        roe_period: '2024_Q4',
        formula: 'P/B = close_vnd / (parent_attributable_equity_billion_vnd * 1e9 / listed_shares)'
      }
    }
  ]
};

const mockValuationUnconfigured: MarketValuationResponse = {
  configured: false,
  source: 'SSI FastConnect Data',
  stale: false,
  items: []
};

const mockReportVCB: AdaptiveReportResponse = {
  report_version: 'er-report-v1',
  report_spec: {
    kind: 'note',
    target_ticker: 'VCB',
    blocks: [
      {
        type: 'headline',
        sentence: {
          sentence_id: 's1',
          text: 'VCB đạt tăng trưởng ổn định với tỷ suất sinh lời vượt trội.',
          fact_ids: ['f1'],
          author: 'orchestrator',
          source: 'model',
          revision: 1
        }
      }
    ]
  },
  target_ticker: 'VCB',
  question_type: 'company_profile',
  facts: [
    {
      fact_id: 'f1',
      entity_id: 'VCB',
      metric_id: 'roe',
      period: '2024_Q4',
      value: 19.5,
      fact_type: 'value'
    }
  ],
  datasets: [],
  source_notes: []
} as unknown as AdaptiveReportResponse;

const mockSectorReport: AdaptiveReportResponse = {
  report_version: 'er-report-v1',
  report_spec: {
    kind: 'note',
    blocks: [
      {
        type: 'headline',
        sentence: {
          sentence_id: 's2',
          text: 'Toàn cảnh chất lượng tài sản và định giá các ngân hàng HOSE.',
          fact_ids: ['f_top', 'f_bot'],
          author: 'orchestrator',
          source: 'model',
          revision: 1
        }
      }
    ]
  },
  question_type: 'ranking',
  facts: [
    {
      fact_id: 'f_top',
      entity_id: 'ACB',
      metric_id: 'roe',
      period: '2024_Q4',
      value: 1,
      rank_better: 1,
      denominator: 10,
      fact_type: 'peer_rank'
    },
    {
      fact_id: 'f_bot',
      entity_id: 'STB',
      metric_id: 'roe',
      period: '2024_Q4',
      value: 10,
      rank_better: 10,
      denominator: 10,
      fact_type: 'peer_rank'
    }
  ],
  datasets: [],
  source_notes: []
} as unknown as AdaptiveReportResponse;

describe('MarketPriceStrip', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders all 10 tickers with formatted prices and changes when configured', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesConfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    render(<MarketPriceStrip />, { wrapper: createWrapper() });

    expect(await screen.findAllByText('VCB')).toHaveLength(2); // Double copy for marquee
    expect(screen.getAllByText('ACB')).toHaveLength(2);
    expect(screen.getAllByText('BID')).toHaveLength(2);
    expect(screen.getAllByText('CTG')).toHaveLength(2);
    expect(screen.getAllByText('HDB')).toHaveLength(2);
    expect(screen.getAllByText('MBB')).toHaveLength(2);
    expect(screen.getAllByText('SHB')).toHaveLength(2);
    expect(screen.getAllByText('STB')).toHaveLength(2);
    expect(screen.getAllByText('TCB')).toHaveLength(2);
    expect(screen.getAllByText('VPB')).toHaveLength(2);

    expect(screen.getAllByText('91.800')).toHaveLength(2);
    expect(screen.getAllByText('+0.33%')).toHaveLength(2);
    expect(screen.getAllByText('-0.62%')).toHaveLength(2);
  });

  it('displays amber badge "dữ liệu trễ" when stale: true', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesStale), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    render(<MarketPriceStrip />, { wrapper: createWrapper() });

    expect(await screen.findByText('dữ liệu trễ')).toBeInTheDocument();
  });

  it('hides cleanly without rendering anything when quotes: [] or unconfigured', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesUnconfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    const { container } = render(<MarketPriceStrip />, { wrapper: createWrapper() });
    await new Promise((r) => setTimeout(r, 50));
    expect(container).toBeEmptyDOMElement();
  });
});

describe('WorkspaceShell ticker integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders shell marquee ticker merged into the header row on the right with containment', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesConfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    render(
      <WorkspaceShell activeSection="analysis">
        <div data-testid="page-content">Trang phân tích</div>
      </WorkspaceShell>,
      { wrapper: createWrapper() }
    );

    // Header has the ticker region once
    const tickers = await screen.findAllByRole('region', {
      name: /Bảng giá thị trường SSI 10 ngân hàng HOSE/i
    });
    expect(tickers).toHaveLength(1);
    const ticker = tickers[0];
    expect(ticker).toHaveClass('ticker-container');
    expect(ticker).toHaveClass('overflow-hidden');
    expect(ticker.parentElement).toHaveClass('overflow-hidden');
    expect(ticker.parentElement).toHaveClass('hidden');
    expect(ticker.parentElement).toHaveClass('lg:flex');
    expect(screen.getByTestId('page-content')).toBeInTheDocument();
  });
});

describe('ReportMarketRow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders market row inside report with 4 tiles and quiet footer for focal bank', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesConfigured), { status: 200 }));
      }
      if (url.includes('/api/market/valuation')) {
        return Promise.resolve(new Response(JSON.stringify(mockValuationConfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    render(<ReportMarketRow report={mockReportVCB} />, { wrapper: createWrapper() });

    expect(await screen.findByRole('region', { name: /Bối cảnh thị trường trong báo cáo/i })).toBeInTheDocument();
    expect(screen.getByText('Thị trường')).toBeInTheDocument();
    expect(screen.getByText('VCB')).toBeInTheDocument();

    // 4 tiles
    expect(screen.getByText('Giá đóng cửa')).toBeInTheDocument();
    expect(screen.getByText('91.800 đ')).toBeInTheDocument();

    expect(screen.getByText('Biến động phiên')).toBeInTheDocument();
    expect(screen.getByText('+0.33%')).toBeInTheDocument();

    expect(screen.getByText('P/B (Định giá)')).toBeInTheDocument();
    expect(screen.getByText('1.91x')).toBeInTheDocument();

    expect(screen.getByText('ROE (BCTC)')).toBeInTheDocument();
    expect(screen.getByText('19.50%')).toBeInTheDocument();

    // Quiet footer
    expect(
      screen.getByText(/Nguồn: SSI FastConnect Data · Phiên 12\/10\/2026 .* Tham khảo ngoài báo cáo thẩm định/)
    ).toBeInTheDocument();
  });

  it('renders top and bottom ranking banks for sector/ranking report', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesConfigured), { status: 200 }));
      }
      if (url.includes('/api/market/valuation')) {
        return Promise.resolve(new Response(JSON.stringify(mockValuationConfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    render(<ReportMarketRow report={mockSectorReport} />, { wrapper: createWrapper() });

    expect(await screen.findByText('ACB')).toBeInTheDocument();
    expect(screen.getByText('(Đầu nhóm)')).toBeInTheDocument();

    expect(screen.getByText('STB')).toBeInTheDocument();
    expect(screen.getByText('(Cuối nhóm)')).toBeInTheDocument();
  });

  it('hides cleanly when unconfigured or empty-down with zero empty frames', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesUnconfigured), { status: 200 }));
      }
      if (url.includes('/api/market/valuation')) {
        return Promise.resolve(new Response(JSON.stringify(mockValuationUnconfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    const { container } = render(<ReportMarketRow report={mockReportVCB} />, { wrapper: createWrapper() });
    await new Promise((r) => setTimeout(r, 50));
    expect(container).toBeEmptyDOMElement();
  });

  it('shows stale badge when market data is stale', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesStale), { status: 200 }));
      }
      if (url.includes('/api/market/valuation')) {
        return Promise.resolve(new Response(JSON.stringify({ ...mockValuationConfigured, stale: true }), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    render(<ReportMarketRow report={mockReportVCB} />, { wrapper: createWrapper() });

    expect(await screen.findByText('dữ liệu trễ')).toBeInTheDocument();
  });
});

describe('AdaptiveReport integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders ReportMarketRow directly inside the report under KPI band and removes old floating card', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesConfigured), { status: 200 }));
      }
      if (url.includes('/api/market/valuation')) {
        return Promise.resolve(new Response(JSON.stringify(mockValuationConfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    render(<AdaptiveReport report={mockReportVCB} />, { wrapper: createWrapper() });

    // The old floating black card title does NOT exist
    expect(screen.queryByText('Bối cảnh thị trường & Định giá')).not.toBeInTheDocument();

    // The new ReportMarketRow is inside
    expect(await screen.findByRole('region', { name: /Bối cảnh thị trường trong báo cáo/i })).toBeInTheDocument();
    expect(screen.getByText('Giá đóng cửa')).toBeInTheDocument();
    expect(screen.getByText('91.800 đ')).toBeInTheDocument();
  });
});

describe('Fresh result view in AnalysisSessionWorkspace', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders freshly generated report with market row immediately without extra clicks', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesConfigured), { status: 200 }));
      }
      if (url.includes('/api/market/valuation')) {
        return Promise.resolve(new Response(JSON.stringify(mockValuationConfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    render(
      <AnalysisSessionWorkspace
        isLiveStream={false}
        report={mockReportVCB}
        steps={[
          {
            step_id: 'step-done',
            seq: 1,
            t_ms: 1000,
            kind: 'report_ready',
            actor: 'orchestrator',
            recipient: null,
            summary: 'Báo cáo sẵn sàng',
            detail: { report_id: 'rep-fresh-1' }
          }
        ]}
      />,
      { wrapper: createWrapper() }
    );

    // Fresh result section is immediately visible
    expect(await screen.findByRole('region', { name: /Bối cảnh thị trường trong báo cáo/i })).toBeInTheDocument();
    expect(screen.getByText('91.800 đ')).toBeInTheDocument();
    expect(screen.getByText('+0.33%')).toBeInTheDocument();
  });
});

describe('ValuationScatterChart', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders scatter chart with light styling, formula footnote, and STB footnote when ROE is > 8 points below median', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesConfigured), { status: 200 }));
      }
      if (url.includes('/api/market/valuation')) {
        return Promise.resolve(new Response(JSON.stringify(mockValuationConfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    render(<ValuationScatterChart focalTicker="VCB" />, { wrapper: createWrapper() });

    // Collapsed header is rendered
    expect(await screen.findByText(/Bối cảnh thị trường: Định giá P\/B so với ROE/)).toBeInTheDocument();

    // Toggle open
    fireEvent.click(screen.getByRole('button', { name: /Bối cảnh thị trường/i }));

    // Footnote formula is visible
    expect(screen.getByText(/Công thức: P\/B = Giá đóng cửa/)).toBeInTheDocument();
    expect(screen.getByText(/Bối cảnh thị trường tham khảo bên cạnh báo cáo thẩm định/)).toBeInTheDocument();

    // STB footnote is displayed because STB ROE (10.2%) is > 8 points below median (19.5%)
    expect(screen.getByText('* STB: ROE thấp hơn nhóm.')).toBeInTheDocument();
  });

  it('displays 10-ticker compact chips for sector/ranking reports without a single focal bank', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesConfigured), { status: 200 }));
      }
      if (url.includes('/api/market/valuation')) {
        return Promise.resolve(new Response(JSON.stringify(mockValuationConfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    render(<ValuationScatterChart defaultExpanded={true} report={mockSectorReport} />, { wrapper: createWrapper() });

    expect(await screen.findByRole('group', { name: /Thống kê định giá 10 ngân hàng/i })).toBeInTheDocument();
    expect(screen.getByText('Bảng giá & định giá 10 ngân hàng HOSE')).toBeInTheDocument();
  });

  it('hides cleanly when unconfigured', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/valuation')) {
        return Promise.resolve(new Response(JSON.stringify(mockValuationUnconfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    const { container } = render(<ValuationScatterChart focalTicker="VCB" />, { wrapper: createWrapper() });
    await new Promise((r) => setTimeout(r, 50));
    expect(container).toBeEmptyDOMElement();
  });
});

describe('readingWording utilities', () => {
  it('formats reading methods accurately in Vietnamese', () => {
    expect(formatReadingMethod('single')).toBe('Đối soát đơn (single)');
    expect(formatReadingMethod('confirmed')).toBe('Đối soát xác nhận (confirmed)');
    expect(formatReadingMethod('confirmed_ocr_twice')).toBe('Đối soát kép qua OCR (confirmed_ocr_twice)');
    expect(formatReadingMethod('visual')).toBe('Đối soát trực quan (visual)');
    expect(formatReadingMethod('comparative_only')).toBe('Kỳ so sánh (comparative_only)');
    expect(formatReadingMethod(undefined)).toBeNull();
  });

  it('extracts leaf source metadata properly', () => {
    const meta = findLeafSourceMetadata({
      observation_id: 'obs-parent',
      entity: 'VCB',
      metric: 'roe',
      period: '2024_Q4',
      children: [
        {
          observation_id: 'obs-leaf',
          entity: 'VCB',
          metric: 'equity',
          period: '2024_Q4',
          row_label: 'Cho vay khach hang',
          reading: 'confirmed',
          section: 'Thuyet minh',
          page: 12,
          children: []
        }
      ]
    });
    expect(meta.section).toBe('Thuyet minh');
    expect(meta.rowLabel).toBe('Cho vay khach hang');
    expect(meta.reading).toBe('confirmed');
    expect(meta.page).toBe(12);

    const detail = buildInputStepDetail(meta.rowLabel, meta.reading);
    expect(detail).toContain("Trích xuất từ chỉ tiêu 'Cho vay khach hang'");
    expect(detail).toContain('Đối soát xác nhận (confirmed)');
  });

  it('builds audit verdict presentation without false claims', () => {
    const verdict = buildAuditVerdictPresentation({
      status: 'verified',
      reason: 'Đạt kiểm định đối soát độc lập'
    });
    expect(verdict).not.toBeNull();
    expect(verdict?.title).toBe('Kết quả thẩm định đối soát');
    expect(verdict?.badge).toBe('Verified');
    expect(verdict?.detail).toBe('Đạt kiểm định đối soát độc lập');

    const unverified = buildAuditVerdictPresentation(null);
    expect(unverified).toBeNull();
  });
});
