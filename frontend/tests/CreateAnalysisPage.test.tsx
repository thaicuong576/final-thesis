import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CreateAnalysisPage } from '../src/pages/create-analysis/CreateAnalysisPage';
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

  it('selects default metrics from a topic preset', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /Chất lượng tài sản/ }));
    expect(screen.getByText('NPL')).toBeInTheDocument();
    expect(screen.getByText('Coverage')).toBeInTheDocument();
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

  it('reflects the form state in the request summary', async () => {
    const user = userEvent.setup();
    renderPage();
    await fillValidScope(user);
    const summary = screen.getByRole('complementary', { name: 'Tóm tắt yêu cầu' });
    expect(summary).toHaveTextContent('ACB');
    expect(summary).toHaveTextContent('Q1/2024');
    expect(summary).toHaveTextContent('NPL · Coverage');
  });
});
