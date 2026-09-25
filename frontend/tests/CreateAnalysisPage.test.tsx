import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CreateAnalysisPage } from '../src/pages/create-analysis/CreateAnalysisPage';
import { capabilityService } from '../src/entities/capability/api/capabilityService';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';
import type { AnalysisCapabilities } from '../src/entities/capability/model/types';

function capabilities(overrides: Partial<AnalysisCapabilities> = {}): AnalysisCapabilities {
  return {
    ...mockCapabilities,
    analysis_available: true,
    implemented_capabilities: ['company'],
    dataset_snapshot_id: 'snapshot-company-1',
    database_status: 'connected',
    ...overrides
  };
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={['/analysis']}>
      <QueryClientProvider client={client}><CreateAnalysisPage /></QueryClientProvider>
    </MemoryRouter>
  );
}

describe('CreateAnalysisPage API truth and execution gates', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities());
  });

  it('shows API catalog separately from runnable snapshot and does not offer suggestions while unavailable', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      analysis_available: false,
      implemented_capabilities: [],
      dataset_snapshot_id: null,
      database_status: 'disconnected'
    }));

    renderPage();

    expect(await screen.findByText('Phạm vi dữ liệu API công bố')).toBeInTheDocument();
    expect(screen.getByText(/Snapshot đã kiểm định: chưa có/)).toBeInTheDocument();
    expect(screen.getByText(/API chưa xác nhận snapshot doanh nghiệp khả dụng/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Phân tích NPL · ACB/ })).not.toBeInTheDocument();
  });

  it('builds suggested company questions from provider catalog scope', async () => {
    renderPage();

    const suggestion = await screen.findByRole('button', { name: /Phân tích NPL · ACB/ });
    await userEvent.setup().click(suggestion);

    const composer = screen.getByRole('textbox', { name: 'Câu hỏi phân tích' });
    expect(composer).toHaveValue('Phân tích NPL của ACB trong năm 2024.');
    expect(screen.getAllByText('Q1–Q4/2024').length).toBeGreaterThan(0);
    expect(screen.getByText('Chất lượng tài sản')).toBeInTheDocument();
  });

  it('blocks an otherwise valid company question until the API confirms a runnable snapshot', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(capabilities({
      analysis_available: false,
      implemented_capabilities: [],
      dataset_snapshot_id: null,
      database_status: 'disconnected'
    }));
    const user = userEvent.setup();
    renderPage();

    const composer = await screen.findByRole('textbox', { name: 'Câu hỏi phân tích' });
    await user.type(composer, 'Phân tích ROE của TCB trong năm 2024.');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/chưa xác nhận có snapshot dữ liệu đã kiểm định/i);
    expect(screen.getByRole('button', { name: /Xác nhận & phân tích/ })).toBeDisabled();
  });

  it('blocks requests for peer comparison when only company capability is implemented', async () => {
    const user = userEvent.setup();
    renderPage();

    const composer = await screen.findByRole('textbox', { name: 'Câu hỏi phân tích' });
    await user.type(composer, 'So sánh ROE của ACB và TCB trong năm 2024.');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/chưa triển khai năng lực sector/i);
    expect(screen.getByRole('button', { name: /Xác nhận & phân tích/ })).toBeDisabled();
  });

  it('does not silently select the first bank when a question omits its target', async () => {
    const user = userEvent.setup();
    renderPage();

    const composer = await screen.findByRole('textbox', { name: 'Câu hỏi phân tích' });
    await user.type(composer, 'Phân tích ROE trong năm 2024.');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/Câu hỏi chưa nêu rõ/i);
    expect(screen.getByRole('button', { name: /Xác nhận & phân tích/ })).toBeDisabled();
  });
});
