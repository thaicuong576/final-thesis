import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DataPage } from '../src/pages/data/DataPage';
import { capabilityService } from '../src/entities/capability/api/capabilityService';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';
import { stagingCapabilitiesFixture } from '../src/test/fixtures/stagingCapabilitiesFixture';
import type { AnalysisCapabilities } from '../src/entities/capability/model/types';

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

describe('DataPage catalog and readiness', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities());
  });

  it('keeps provider catalog visible while clearly blocking an unavailable snapshot', async () => {
    renderDataPage();

    expect(await screen.findByRole('heading', { name: 'Dữ liệu phân tích' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Chưa thể chạy phân tích trên dữ liệu hiện tại' })).toBeInTheDocument();
    expect(screen.getByText(/Mã catalog:/)).toBeInTheDocument();
    expect(screen.getByText(/Snapshot đã kiểm định: chưa công bố/)).toBeInTheDocument();
    expect(screen.getByText('Ngân hàng trong catalog')).toBeInTheDocument();
    expect(screen.getByText(/ACB \(Ngân hàng Á Châu\)/)).toBeInTheDocument();
    expect(screen.getAllByText(/Trạng thái kho dữ liệu: disconnected/).length).toBeGreaterThan(0);
    expect(screen.getByText('API chưa xác nhận phân tích nhóm tham chiếu có thể chạy.')).toBeInTheDocument();
    expect(screen.getByText('API chưa xác nhận năng lực phân tích vĩ mô có thể chạy.')).toBeInTheDocument();
    expect(screen.getByText(/Nguồn, phiên bản dữ liệu và thời điểm kiểm định chưa được xác nhận/)).toBeInTheDocument();
    expect(screen.queryByText(mockCapabilities.source!)).not.toBeInTheDocument();
    expect(screen.queryByText(mockCapabilities.macro.summary)).not.toBeInTheDocument();
    expect(screen.queryByText('5 ngân hàng: acb, tcb, vpb, mbb, vcb')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Thêm nguồn dữ liệu|Kết nối nguồn mới/ })).not.toBeInTheDocument();
  });

  it('renders the API catalog counts without substituting the older frontend sample', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      entities: Array.from({ length: 27 }, (_, index) => ({ id: `bank-${index}`, ticker: `B${index}`, name: `Bank ${index}` })),
      metrics: Array.from({ length: 7 }, (_, index) => ({ id: `metric-${index}`, acronym: `M${index}`, label: `Metric ${index}`, topicId: 'catalog' }))
    }));

    renderDataPage();

    expect(await screen.findByText('27')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText(/B0 \(Bank 0\) · B1 \(Bank 1\)/)).toBeInTheDocument();
    expect(screen.queryByText(/ACB · TCB · VPB · MBB · VCB/)).not.toBeInTheDocument();
  });

  it('shows a provider-backed runnable company snapshot when the API confirms it', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      analysis_available: true,
      dataset_snapshot_id: 'provider-snapshot-42',
      implemented_capabilities: ['company'],
      database_status: 'connected'
    }));

    renderDataPage();

    expect(await screen.findByText('Snapshot đã kiểm định: provider-snapshot-42')).toBeInTheDocument();
    expect(screen.getByText('Có')).toBeInTheDocument();
    expect(screen.getByText('Doanh nghiệp')).toBeInTheDocument();
  });

  it('uses the API sector capability to mark the catalog peer universe as runnable', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      analysis_available: true,
      dataset_snapshot_id: 'provider-snapshot-42',
      implemented_capabilities: ['company', 'sector'],
      database_status: 'connected'
    }));

    renderDataPage();

    expect(await screen.findByText('5 ngân hàng: acb, tcb, vpb, mbb, vcb')).toBeInTheDocument();
    expect(screen.getByText(mockCapabilities.peerUniverse!.description)).toBeInTheDocument();
  });

  it('renders Vietnamese metric labels and units in the metrics table', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      analysis_available: true,
      dataset_snapshot_id: 'gold-v5-snap',
      database_status: 'connected'
    }));

    renderDataPage();

    expect(await screen.findByRole('heading', { name: /Chỉ tiêu tài chính/ })).toBeInTheDocument();
    expect(screen.getByText('Tỷ lệ nợ xấu')).toBeInTheDocument();
    expect(screen.getByText('Tỷ lệ bao phủ nợ xấu')).toBeInTheDocument();
    expect(screen.getByText('Tỷ suất sinh lời trên tài sản')).toBeInTheDocument();
    expect(screen.getByText('Tỷ suất sinh lời trên vốn chủ sở hữu')).toBeInTheDocument();
    const percentUnits = screen.getAllByText('%');
    expect(percentUnits.length).toBeGreaterThanOrEqual(4);
  });

  it('renders enterprise list in catalog overview without separate redundant enterprise table', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      analysis_available: true,
      dataset_snapshot_id: 'gold-v5-snap',
      database_status: 'connected'
    }));

    renderDataPage();

    expect(await screen.findByRole('heading', { name: 'Catalog năng lực API' })).toBeInTheDocument();
    expect(screen.getByText(/ACB \(Ngân hàng Á Châu\)/)).toBeInTheDocument();
    expect(screen.getByText(/TCB \(Ngân hàng Kỹ thương Việt Nam\)/)).toBeInTheDocument();
    expect(screen.getByText(/VCB \(Ngân hàng Ngoại thương Việt Nam\)/)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /Danh sách doanh nghiệp/ })).not.toBeInTheDocument();
  });

  it('renders realistic staging capabilities fixture with friendly labels, single action button, and neutral note', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(stagingCapabilitiesFixture);

    renderDataPage();

    expect(await screen.findByRole('heading', { name: 'Catalog năng lực API' })).toBeInTheDocument();

    // Single "Tạo phân tích" button at top header only
    const createAnalysisLinks = screen.getAllByRole('link', { name: /Tạo phân tích/i });
    expect(createAnalysisLinks.length).toBe(1);

    // 5 enterprises formatted cleanly (name === ticker, so no redundant parens)
    expect(screen.getByText('ACB · TCB · VPB · MBB · VCB')).toBeInTheDocument();

    // 4 metrics with clean symbols (LLR, NPL, ROA, ROE instead of LLR_COVERAGE, NPL_G35)
    expect(screen.getByText('NPL · LLR · ROA · ROE')).toBeInTheDocument();

    // 4 metrics in table
    expect(screen.getByRole('heading', { name: /Chỉ tiêu tài chính \(4\)/ })).toBeInTheDocument();
    expect(screen.getByText('Tỷ lệ nợ xấu (nhóm 3–5)')).toBeInTheDocument();
    expect(screen.getByText('Tỷ lệ bao phủ nợ xấu')).toBeInTheDocument();
    expect(screen.getByText('Tỷ suất sinh lời trên tổng tài sản')).toBeInTheDocument();
    expect(screen.getByText('Tỷ suất sinh lời trên vốn chủ sở hữu')).toBeInTheDocument();
    const percentUnits = screen.getAllByText('%');
    expect(percentUnits.length).toBeGreaterThanOrEqual(4);

    // Friendly periods format: Q1–Q4/2024
    expect(screen.getByText('Q1–Q4/2024')).toBeInTheDocument();

    // Peer group formatted in Vietnamese: "5 ngân hàng: ACB, TCB, VPB, MBB, VCB"
    expect(screen.getByText('5 ngân hàng: ACB, TCB, VPB, MBB, VCB')).toBeInTheDocument();
    expect(screen.getByText('Nhóm 5 ngân hàng niêm yết được kiểm định trong snapshot Gold.')).toBeInTheDocument();

    // Capabilities formatted in Vietnamese: "Doanh nghiệp · Nhóm ngành"
    expect(screen.getByText('Doanh nghiệp · Nhóm ngành')).toBeInTheDocument();

    // Neutral disclaimer inside catalog card
    expect(screen.getByText(/Ô thiếu số liệu đã kiểm định sẽ được ghi rõ trong từng báo cáo/)).toBeInTheDocument();

    // NO separate scope matrix or enterprise tables
    expect(screen.queryByRole('heading', { name: /Phạm vi dữ liệu/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /Danh sách doanh nghiệp/ })).not.toBeInTheDocument();
    expect(screen.queryByText('Trong phạm vi')).not.toBeInTheDocument();
    expect(screen.queryByText('Đã kiểm định')).not.toBeInTheDocument();
    expect(screen.queryByText('chưa có số liệu đã kiểm định')).not.toBeInTheDocument();
  });

  it('only displays entity name in catalog when distinct from ticker', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      analysis_available: true,
      dataset_snapshot_id: 'gold-v5-snap',
      database_status: 'connected',
      entities: [
        { id: 'ACB', ticker: 'ACB', name: 'ACB', type: 'company' },
        { id: 'MBB', ticker: 'MBB', name: 'Ngân hàng Quân Đội', type: 'company' }
      ]
    }));

    renderDataPage();

    expect(await screen.findByRole('heading', { name: 'Catalog năng lực API' })).toBeInTheDocument();
    // Non-distinct entity renders only ticker; distinct entity renders ticker with name in parens
    expect(screen.getByText('ACB · MBB (Ngân hàng Quân Đội)')).toBeInTheDocument();
  });

  it('ensures responsive classes to prevent horizontal page overflow at 375px', async () => {
    const { container } = renderDataPage();

    await screen.findByRole('heading', { name: 'Catalog năng lực API' });

    // Root wrapper has overflow-x-hidden and max-w-full
    const rootWrapper = container.querySelector('.overflow-x-hidden');
    expect(rootWrapper).toBeInTheDocument();
    expect(rootWrapper).toHaveClass('w-full', 'max-w-full', 'min-w-0');

    // Table container has overflow-x-auto
    const tableWrapper = container.querySelector('.overflow-x-auto');
    expect(tableWrapper).toBeInTheDocument();
    expect(tableWrapper).toHaveClass('w-full', 'max-w-full', 'min-w-0');

    // Snapshot ID has break-all to prevent pushing layout
    const snapshotText = screen.getByText(/Mã catalog:/);
    expect(snapshotText).toHaveClass('break-all');
  });

  it('renders error state with retry button and does not fall back to mock data or display fake numbers when API fails', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockRejectedValue(new Error('Máy chủ API không phản hồi (500)'));

    renderDataPage();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Không thể xác định dữ liệu đang hỗ trợ')).toBeInTheDocument();
    expect(screen.getByText(/Máy chủ API không phản hồi \(500\)/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Thử tải lại' })).toBeInTheDocument();

    // Verify NO mock catalog or fake numbers are rendered
    expect(screen.queryByText('Catalog năng lực API')).not.toBeInTheDocument();
    expect(screen.queryByText('Ngân hàng trong catalog')).not.toBeInTheDocument();
    expect(screen.queryByText('Chỉ tiêu trong catalog')).not.toBeInTheDocument();
    expect(screen.queryByText('Ma trận độ phủ doanh nghiệp × kỳ')).not.toBeInTheDocument();
    expect(screen.queryByText('Phạm vi dữ liệu: Doanh nghiệp × Kỳ')).not.toBeInTheDocument();
    expect(screen.queryByText('Danh sách doanh nghiệp')).not.toBeInTheDocument();
    expect(screen.queryByText(/ACB · TCB · VPB · MBB · VCB/)).not.toBeInTheDocument();
  });

  it('renders clean empty state when API returns empty catalog', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      entities: [],
      metrics: [],
      periods: []
    }));

    renderDataPage();

    expect(await screen.findByRole('region', { name: 'Dữ liệu rỗng' })).toBeInTheDocument();
    expect(screen.getByText('Chưa có dữ liệu phân tích')).toBeInTheDocument();
    expect(screen.getByText(/API hiện chưa công bố dữ liệu hoặc snapshot đã kiểm định nào/)).toBeInTheDocument();
    expect(screen.queryByText('Catalog năng lực API')).not.toBeInTheDocument();
  });
});
