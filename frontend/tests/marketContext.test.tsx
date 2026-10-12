import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MarketPriceStrip } from '../src/features/market-context/MarketPriceStrip';
import { FocalValuationCard } from '../src/features/market-context/FocalValuationCard';
import { ValuationScatterChart } from '../src/features/market-context/ValuationScatterChart';
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
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
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
    }
  ]
};

const mockValuationUnconfigured: MarketValuationResponse = {
  configured: false,
  source: 'SSI FastConnect Data',
  stale: false,
  items: []
};

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

    expect(await screen.findByText('VCB')).toBeInTheDocument();
    expect(screen.getByText('ACB')).toBeInTheDocument();
    expect(screen.getByText('BID')).toBeInTheDocument();
    expect(screen.getByText('CTG')).toBeInTheDocument();
    expect(screen.getByText('HDB')).toBeInTheDocument();
    expect(screen.getByText('MBB')).toBeInTheDocument();
    expect(screen.getByText('SHB')).toBeInTheDocument();
    expect(screen.getByText('STB')).toBeInTheDocument();
    expect(screen.getByText('TCB')).toBeInTheDocument();
    expect(screen.getByText('VPB')).toBeInTheDocument();

    expect(screen.getByText('91.800')).toBeInTheDocument();
    expect(screen.getByText('+0.33%')).toBeInTheDocument();
    expect(screen.getByText('-0.62%')).toBeInTheDocument();
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

  it('hides cleanly without rendering anything when configured: false', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/market/quotes')) {
        return Promise.resolve(new Response(JSON.stringify(mockQuotesUnconfigured), { status: 200 }));
      }
      return Promise.reject(new Error('not handled'));
    });

    const { container } = render(<MarketPriceStrip />, { wrapper: createWrapper() });

    // Wait microtask
    await new Promise((r) => setTimeout(r, 50));
    expect(container).toBeEmptyDOMElement();
  });
});

describe('FocalValuationCard', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('displays focal ticker price, change, P/B and ROE', async () => {
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

    render(<FocalValuationCard ticker="VCB" />, { wrapper: createWrapper() });

    expect(await screen.findByText('Bối cảnh thị trường & Định giá')).toBeInTheDocument();
    expect(screen.getByText('VCB')).toBeInTheDocument();
    expect(screen.getByText('91.800 đ')).toBeInTheDocument();
    expect(screen.getByText('1.91x')).toBeInTheDocument();
    expect(screen.getByText('19.50%')).toBeInTheDocument();
    expect(screen.getByText(/Nguồn: SSI FastConnect Data/)).toBeInTheDocument();
  });

  it('hides cleanly when unconfigured', async () => {
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

    const { container } = render(<FocalValuationCard ticker="VCB" />, { wrapper: createWrapper() });
    await new Promise((r) => setTimeout(r, 50));
    expect(container).toBeEmptyDOMElement();
  });
});

describe('ValuationScatterChart', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders scatter chart with footnote and focal ticker highlight', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
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
