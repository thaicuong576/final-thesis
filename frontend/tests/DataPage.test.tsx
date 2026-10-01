import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DataPage } from '../src/pages/data/DataPage';
import { capabilityService } from '../src/entities/capability/api/capabilityService';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';
import type { AnalysisCapabilities, CoverageItem } from '../src/entities/capability/model/types';
import { analyticalPeriodIds } from '../src/entities/capability/model/coverage';

const ALL = ['bank.npl_g35', 'bank.llr_coverage', 'bank.roa', 'bank.roe'];

function renderDataPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={['/data']}>
      <QueryClientProvider client={client}><DataPage /></QueryClientProvider>
    </MemoryRouter>
  );
}

function capabilities(overrides: Partial<AnalysisCapabilities> = {}): AnalysisCapabilities {
  return {
    ...mockCapabilities,
    analysis_available: false,
    dataset_snapshot_id: null,
    implemented_capabilities: [],
    database_status: 'disconnected',
    ...overrides
  };
}

/** Two banks, an input-only prior period, three analytical quarters and one missing cell. */
function quarterlyCaps(): AnalysisCapabilities {
  const periods = ['2023_Q4', '2024_Q1', '2024_Q2', '2025_Q1'];
  const coverage: CoverageItem[] = [];
  for (const bank of ['AAA', 'BBB']) {
    for (const p of periods) {
      let metrics = p === '2023_Q4' ? [] : ALL;
      if (bank === 'BBB' && p === '2024_Q2') metrics = [];
      if (bank === 'AAA' && p === '2025_Q1') metrics = ALL.slice(0, 2);
      coverage.push({ entity_id: bank, period_id: p, metrics });
    }
  }
  return capabilities({
    analysis_available: true,
    dataset_snapshot_id: 'snapshot-test',
    implemented_capabilities: ['company', 'sector'],
    database_status: 'connected',
    entities: [
      { id: 'AAA', ticker: 'AAA', name: 'Ngân hàng A' },
      { id: 'BBB', ticker: 'BBB', name: 'Ngân hàng B' }
    ],
    periods: periods.map((id) => ({ id, label: id })) as AnalysisCapabilities['periods'],
    metrics: ALL.map((id) => ({ id, acronym: id.split('.')[1].toUpperCase(), label: id, topicId: 'x', direction: 'higher_is_better' })),
    coverage
  });
}

describe('DataPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities());
  });

  it('says plainly when analysis cannot run and invents no source or coverage', async () => {
    renderDataPage();
    expect(await screen.findByRole('heading', { name: 'Dữ liệu đang dùng để phân tích' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Chưa thể chạy phân tích' })).toBeInTheDocument();
    expect(screen.queryByTestId('coverage-matrix-table')).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Đặt câu hỏi/ })).not.toBeInTheDocument();
  });

  it('offers only quarters that carry metrics, not input-only prior periods', () => {
    expect(analyticalPeriodIds(quarterlyCaps())).toEqual(['2024_Q1', '2024_Q2', '2025_Q1']);
  });

  it('summarises banks, quarter range and full cells from API coverage', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(quarterlyCaps());
    renderDataPage();
    const stats = await screen.findByTestId('dataset-stats');
    expect(within(stats).getByText('Q1/2024 – Q1/2025')).toBeInTheDocument();
    // 2 banks × 3 quarters = 6 cells; BBB 2024_Q2 is missing and AAA 2025_Q1 is partial.
    expect(within(stats).getByText('4/6')).toBeInTheDocument();
    expect(within(stats).getByText('2 ô ngân hàng–quý chưa có báo cáo')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Đặt câu hỏi/ })).toHaveAttribute('href', '/analysis');
  });

  it('marks each bank-quarter cell full, partial or missing without imputing', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(quarterlyCaps());
    renderDataPage();
    const table = await screen.findByTestId('coverage-matrix-table');
    expect(within(table).queryByText('Q4')).not.toBeInTheDocument();
    expect(within(table).getByRole('img', { name: 'BBB Q2/2024: chưa có báo cáo' })).toHaveAttribute('data-state', 'missing');
    expect(within(table).getByRole('img', { name: 'AAA Q1/2025: có 2/4 chỉ tiêu' })).toHaveAttribute('data-state', 'partial');
    expect(within(table).getByRole('img', { name: 'AAA Q1/2024: đủ 4 chỉ tiêu' })).toHaveAttribute('data-state', 'full');
    expect(screen.getByTestId('coverage-matrix-scroll').className).toContain('overflow-x-auto');
  });

  it('explains every metric in Vietnamese with its formula', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(quarterlyCaps());
    renderDataPage();
    expect(await screen.findByText('Tỷ suất sinh lời trên vốn chủ sở hữu (ROE)')).toBeInTheDocument();
    expect(screen.getByText('Dư nợ nhóm 3–5 / tổng dư nợ cho vay khách hàng')).toBeInTheDocument();
    expect(screen.queryByText(/Gold v5/)).not.toBeInTheDocument();
  });

  it('shows an error with retry and no fallback numbers when the API fails', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockRejectedValue(new Error('Máy chủ không phản hồi'));
    renderDataPage();
    expect(await screen.findByRole('heading', { name: 'Không tải được phạm vi dữ liệu' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Thử tải lại' })).toBeInTheDocument();
    expect(screen.queryByTestId('dataset-stats')).not.toBeInTheDocument();
  });

  it('renders an empty state when the API publishes no dataset', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({ entities: [], metrics: [], periods: [] }));
    renderDataPage();
    expect(await screen.findByRole('heading', { name: 'Chưa có dữ liệu phân tích' })).toBeInTheDocument();
  });
});
