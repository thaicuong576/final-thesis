import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DataPage } from '../src/pages/data/DataPage';
import { capabilityService } from '../src/entities/capability/api/capabilityService';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';
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
});
