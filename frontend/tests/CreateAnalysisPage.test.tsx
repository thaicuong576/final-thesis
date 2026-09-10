import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CreateAnalysisPage } from '../src/pages/create-analysis/CreateAnalysisPage';
import { analysisService } from '../src/entities/analysis/api/analysisService';
import { capabilityService } from '../src/entities/capability/api/capabilityService';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><CreateAnalysisPage /></QueryClientProvider>);
}

async function fillValidScope(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByRole('heading', { name: 'Tạo phân tích' });
  await user.click(await screen.findByLabelText('ACB'));
  await user.click(await screen.findByLabelText('Q1/2024'));
  await user.click(await screen.findByRole('button', { name: /Chất lượng tài sản/ }));
  await user.type(await screen.findByLabelText(/Mục tiêu phân tích/), 'So sánh chất lượng tài sản của ACB trong Q1/2024.');
}

describe('CreateAnalysisPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('keeps the CTA disabled for an invalid empty form', async () => {
    renderPage();
    expect(await screen.findByRole('button', { name: 'Chạy phân tích' })).toBeDisabled();
  });

  it('enables the CTA for a valid request', async () => {
    const user = userEvent.setup();
    renderPage();
    await fillValidScope(user);
    expect(screen.getByRole('button', { name: 'Chạy phân tích' })).toBeEnabled();
  });

  it('selects default metrics from a topic preset in the request state', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /Chất lượng tài sản/ }));
    await user.click(await screen.findByRole('button', { name: /Tùy chỉnh chỉ tiêu/ }));
    expect(screen.getByLabelText(/NPL — Tỷ lệ nợ xấu/)).toBeChecked();
    expect(screen.getByLabelText(/Coverage — Tỷ lệ bao phủ nợ xấu/)).toBeChecked();
  });

  it('supports custom metric selection and restoring defaults', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /Chất lượng tài sản/ }));
    await user.click(await screen.findByRole('button', { name: /Tùy chỉnh chỉ tiêu/ }));
    await user.click(await screen.findByLabelText(/ROA — Tỷ suất sinh lời trên tài sản/));
    expect(await screen.findByLabelText(/ROA — Tỷ suất sinh lời trên tài sản/)).toBeChecked();
    await user.click(await screen.findByRole('button', { name: /Khôi phục mặc định/ }));
    expect(await screen.findByLabelText(/ROA — Tỷ suất sinh lời trên tài sản/)).not.toBeChecked();
  });

  it('preserves manually kept metrics when their topic is deselected', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /Chất lượng tài sản/ }));
    await user.click(await screen.findByRole('button', { name: /Tùy chỉnh chỉ tiêu/ }));

    const npl = screen.getByLabelText(/NPL — Tỷ lệ nợ xấu/);
    await user.click(npl);
    await user.click(npl);
    await user.click(screen.getByLabelText(/ROA — Tỷ suất sinh lời trên tài sản/));
    await user.click(await screen.findByRole('button', { name: /Chất lượng tài sản/ }));

    expect(screen.getByLabelText(/NPL — Tỷ lệ nợ xấu/)).toBeChecked();
    expect(screen.getByLabelText(/Coverage — Tỷ lệ bao phủ nợ xấu/)).not.toBeChecked();
    expect(screen.getByLabelText(/ROA — Tỷ suất sinh lời trên tài sản/)).toBeChecked();
  });

  it('renders capability counts and period labels from the capability response', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue({
      ...mockCapabilities,
      entities: mockCapabilities.entities.slice(0, 2),
      periods: mockCapabilities.periods.slice(0, 2),
      metrics: mockCapabilities.metrics.slice(0, 1),
      topics: [{ ...mockCapabilities.topics[0], metricIds: ['npl'] }]
    });
    renderPage();
    await screen.findByRole('heading', { name: 'Tạo phân tích' });

    expect(screen.getByText('2 ngân hàng')).toBeInTheDocument();
    expect(screen.getByText('Q1–Q2/2024')).toBeInTheDocument();
    expect(screen.getByText('1 chỉ tiêu')).toBeInTheDocument();
    expect(screen.getAllByText('0/2 đã chọn')).toHaveLength(2);
    expect(screen.getByLabelText('Q1/2024')).toBeInTheDocument();
    expect(screen.getByLabelText('Q2/2024')).toBeInTheDocument();
  });

  it('generates a bounded suggested objective', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByLabelText('ACB'));
    await user.click(await screen.findByLabelText('Q1/2024'));
    await user.click(await screen.findByRole('button', { name: /Chất lượng tài sản/ }));
    await user.click(await screen.findByRole('button', { name: 'Dùng mục tiêu gợi ý' }));
    expect(await screen.findByLabelText(/Mục tiêu phân tích/)).toHaveValue('Phân tích NPL và Coverage của ACB trong Q1/2024, đồng thời đối chiếu với nhóm tham chiếu 5 ngân hàng đã được xác thực.');
  });

  it('does not silently overwrite an edited objective after scope changes', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByLabelText('ACB'));
    await user.click(await screen.findByLabelText('Q1/2024'));
    await user.click(await screen.findByRole('button', { name: /Chất lượng tài sản/ }));
    await user.click(await screen.findByRole('button', { name: 'Dùng mục tiêu gợi ý' }));
    const objective = await screen.findByLabelText(/Mục tiêu phân tích/);
    await user.clear(objective);
    await user.type(objective, 'Mục tiêu đã được chỉnh sửa bởi chuyên gia.');
    await user.click(await screen.findByLabelText('TCB'));
    expect(objective).toHaveValue('Mục tiêu đã được chỉnh sửa bởi chuyên gia.');
    expect(screen.getByText('Phạm vi đã thay đổi. Mục tiêu hiện tại có thể không còn phản ánh lựa chọn mới.')).toBeInTheDocument();
  });

  it('blocks submit when Macro is unavailable', async () => {
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue({
      ...mockCapabilities,
      macro: { ...mockCapabilities.macro, status: 'UNAVAILABLE', minimumContractSatisfied: false }
    });
    const user = userEvent.setup();
    renderPage();
    await fillValidScope(user);
    expect(screen.getByRole('button', { name: 'Chạy phân tích' })).toBeDisabled();
    expect(screen.getByText('Chưa thể chạy')).toBeInTheDocument();
  });

  it('submits the capability snapshot and peer universe without client-owned Macro state', async () => {
    const user = userEvent.setup();
    const submit = vi.spyOn(analysisService, 'submit').mockResolvedValue({
      status: 'CLIENT_VALIDATED',
      readyForBackendSubmission: true,
      requestId: 'test-request',
      message: 'Đã kiểm tra phạm vi phía giao diện.'
    });
    renderPage();
    await fillValidScope(user);
    await user.click(screen.getByRole('button', { name: 'Chạy phân tích' }));

    expect(submit).toHaveBeenCalledWith(expect.objectContaining({
      capabilitySnapshotId: mockCapabilities.snapshotId,
      peerUniverseId: mockCapabilities.peerUniverse.id
    }));
    expect(submit.mock.calls[0][0]).not.toHaveProperty('macroStatus');
  });

  it('reflects the form state in the request summary', async () => {
    const user = userEvent.setup();
    renderPage();
    await fillValidScope(user);
    const summary = screen.getByRole('complementary', { name: 'Tóm tắt yêu cầu' });
    expect(summary).toHaveTextContent('ACB');
    expect(summary).toHaveTextContent('Q1/2024');
    expect(summary).toHaveTextContent('NPL · Coverage');
  });

  it('traps focus in the capability drawer and restores focus after Escape', async () => {
    const user = userEvent.setup();
    renderPage();
    const openButton = await screen.findByRole('button', { name: /Xem chi tiết phạm vi dữ liệu/ });
    await user.click(openButton);
    const closeButton = await screen.findByRole('button', { name: 'Đóng' });

    expect(closeButton).toHaveFocus();
    await user.tab();
    expect(closeButton).toHaveFocus();
    await user.tab({ shift: true });
    expect(closeButton).toHaveFocus();
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(openButton).toHaveFocus();
  });
});
