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
    expect(screen.getByText(/ACB · TCB · VPB · MBB · VCB/)).toBeInTheDocument();
    expect(screen.getAllByText(/Trạng thái kho dữ liệu: disconnected/).length).toBeGreaterThan(0);
    expect(screen.getByText('API chưa xác nhận phân tích nhóm tham chiếu có thể chạy.')).toBeInTheDocument();
    expect(screen.getByText('API chưa xác nhận năng lực phân tích vĩ mô có thể chạy.')).toBeInTheDocument();
    expect(screen.getByText(/Nguồn, phiên bản dữ liệu và thời điểm kiểm định chưa được xác nhận/)).toBeInTheDocument();
    expect(screen.queryByText(mockCapabilities.source!)).not.toBeInTheDocument();
    expect(screen.queryByText(mockCapabilities.macro.summary)).not.toBeInTheDocument();
    expect(screen.queryByText(mockCapabilities.peerUniverse!.label)).not.toBeInTheDocument();
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
    expect(screen.getByText(/B0 · B1 · B2/)).toBeInTheDocument();
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
    expect(screen.getByText('company')).toBeInTheDocument();
  });

  it('uses the API sector capability to mark the catalog peer universe as runnable', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      analysis_available: true,
      dataset_snapshot_id: 'provider-snapshot-42',
      implemented_capabilities: ['company', 'sector'],
      database_status: 'connected'
    }));

    renderDataPage();

    expect(await screen.findByText(mockCapabilities.peerUniverse!.label)).toBeInTheDocument();
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

  it('renders structured enterprise list with ticker, full name, and entity classification', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      analysis_available: true,
      dataset_snapshot_id: 'gold-v5-snap',
      database_status: 'connected'
    }));

    renderDataPage();

    expect(await screen.findByRole('heading', { name: /Danh sách doanh nghiệp/ })).toBeInTheDocument();
    expect(screen.getAllByText('Ngân hàng Á Châu').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Ngân hàng Kỹ thương Việt Nam').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Ngân hàng Ngoại thương Việt Nam').length).toBeGreaterThanOrEqual(1);
    const entityTypes = screen.getAllByText('Ngân hàng niêm yết');
    expect(entityTypes.length).toBe(5);
  });

  it('renders realistic staging capabilities fixture with 5 enterprises, 4 metrics with units, 4 periods, peer universe, and neutral scope cells', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(stagingCapabilitiesFixture);

    renderDataPage();

    // 5 doanh nghiệp
    expect(await screen.findByRole('heading', { name: /Danh sách doanh nghiệp \(5\)/ })).toBeInTheDocument();
    expect(screen.getAllByText('ACB').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('TCB').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('VPB').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('MBB').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('VCB').length).toBeGreaterThanOrEqual(1);

    // 4 chỉ tiêu có đơn vị
    expect(screen.getByRole('heading', { name: /Chỉ tiêu tài chính \(4\)/ })).toBeInTheDocument();
    expect(screen.getByText('Tỷ lệ nợ xấu (nhóm 3–5)')).toBeInTheDocument();
    expect(screen.getByText('Tỷ lệ bao phủ nợ xấu')).toBeInTheDocument();
    expect(screen.getByText('Tỷ suất sinh lời trên tổng tài sản')).toBeInTheDocument();
    expect(screen.getByText('Tỷ suất sinh lời trên vốn chủ sở hữu')).toBeInTheDocument();
    const percentUnits = screen.getAllByText('%');
    expect(percentUnits.length).toBeGreaterThanOrEqual(4);

    // 4 kỳ
    expect(screen.getByText('Q1–Q4/2024')).toBeInTheDocument();
    expect(screen.getByText('Q1 2024')).toBeInTheDocument();
    expect(screen.getByText('Q2 2024')).toBeInTheDocument();
    expect(screen.getByText('Q3 2024')).toBeInTheDocument();
    expect(screen.getByText('Q4 2024')).toBeInTheDocument();

    // Nhóm so sánh
    expect(screen.getByText('Snapshot peer group (5 companies)')).toBeInTheDocument();
    expect(screen.getByText('Nhóm 5 ngân hàng niêm yết được kiểm định trong snapshot Gold.')).toBeInTheDocument();

    // Ghi chú trung tính
    expect(screen.getByText(/Ô thiếu số liệu đã kiểm định sẽ được ghi rõ trong từng báo cáo/)).toBeInTheDocument();

    // KHÔNG có chuỗi "Đã kiểm định" hay "chưa có số liệu đã kiểm định" gắn với từng ô
    expect(screen.queryByText('Đã kiểm định')).not.toBeInTheDocument();
    expect(screen.queryByText('chưa có số liệu đã kiểm định')).not.toBeInTheDocument();
  });

  it('only displays entity name when distinct from ticker', async () => {
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

    expect(await screen.findByRole('heading', { name: /Danh sách doanh nghiệp \(2\)/ })).toBeInTheDocument();
    // Distinct name is rendered (in scope matrix and entity list table)
    expect(screen.getAllByText('Ngân hàng Quân Đội').length).toBe(2);
    // Non-distinct name displays fallback dash in enterprise table
    expect(screen.getByText('—')).toBeInTheDocument();
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
