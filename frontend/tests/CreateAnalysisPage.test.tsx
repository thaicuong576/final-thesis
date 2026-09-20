import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CreateAnalysisPage } from '../src/pages/create-analysis/CreateAnalysisPage';
import { analysisService } from '../src/entities/analysis/api/analysisService';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={['/analysis']}>
      <QueryClientProvider client={client}>
        <CreateAnalysisPage />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

describe('CreateAnalysisPage (Clean-Room Screen 1 - Query-Adaptive)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('passes the 10-second acceptance test: shows active dataset context and hero composer without form-heavy controls', async () => {
    renderPage();

    // 1. Which data source will be used? Answered immediately
    expect(await screen.findByText('Ngân hàng Việt Nam 2024')).toBeInTheDocument();
    expect(screen.getByText('Sẵn sàng')).toBeInTheDocument();
    expect(screen.getByText(/ACB · TCB · VPB · MBB · VCB/)).toBeInTheDocument();
    expect(screen.getAllByText(/Q1–Q4\/2024/).length).toBeGreaterThanOrEqual(1);

    // 2. Where do I ask my analytical question?
    expect(screen.getByRole('heading', { name: 'Bạn muốn phân tích điều gì?' })).toBeInTheDocument();
    const composer = screen.getByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    expect(composer).toBeInTheDocument();

    // 3. CTA is disabled when empty
    expect(screen.getByRole('button', { name: /Bắt đầu phân tích/ })).toBeDisabled();

    // 4. Structured scope checkboxes must NOT dominate the initial screen
    expect(screen.queryByLabelText('ACB')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Q1/2024')).not.toBeInTheDocument();
  });

  it('renders suggested analytical prompts and populates the question without auto-submitting', async () => {
    const user = userEvent.setup();
    renderPage();

    const suggestion = await screen.findByRole('button', {
      name: /Chất lượng tài sản ACB, TCB, MBB/
    });
    expect(suggestion).toBeInTheDocument();

    await user.click(suggestion);

    // Clicking a suggestion populates composer text and reveals Parsed Scope feedback without auto-submitting
    const composer = screen.getByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    expect(composer).toHaveValue(
      'So sánh chất lượng tài sản của ACB, TCB và MBB trong năm 2024 và xác định ngân hàng cải thiện rõ nhất.'
    );

    expect(await screen.findByText('Đã nhận diện:')).toBeInTheDocument();
    expect(screen.getByText('ACB')).toBeInTheDocument();
    expect(screen.getByText('TCB')).toBeInTheDocument();
    expect(screen.getByText('MBB')).toBeInTheDocument();

    // Still on composer screen; user has not confirmed or executed yet
    expect(screen.queryByText('Xác nhận kế hoạch phân tích')).not.toBeInTheDocument();

    // Now user clicks CTA to submit question and transition to interpreted state
    const ctaBtn = screen.getByRole('button', { name: /Bắt đầu phân tích/ });
    expect(ctaBtn).not.toBeDisabled();
    await user.click(ctaBtn);

    expect(await screen.findByText('Hệ thống hiểu yêu cầu')).toBeInTheDocument();
    expect(screen.getByText('Xác nhận kế hoạch phân tích')).toBeInTheDocument();
    expect(screen.getByText(/ACB · TCB · MBB/)).toBeInTheDocument();
  });

  it('correctly produces Company-only interpretation without unselected capabilities', async () => {
    const user = userEvent.setup();
    renderPage();

    const composer = await screen.findByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    await user.type(composer, 'ROE của TCB thay đổi thế nào trong năm 2024?');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    // Interpreted state
    expect(await screen.findByText('Hệ thống hiểu yêu cầu')).toBeInTheDocument();
    expect(screen.getByText('Xác nhận kế hoạch phân tích')).toBeInTheDocument();

    // Scope recognition
    expect(screen.getByText('Phạm vi hệ thống nhận diện')).toBeInTheDocument();
    expect(screen.getByText('TCB · Q1–Q4/2024 · ROE')).toBeInTheDocument();

    // Query-adaptive capabilities
    expect(screen.getByText('Phân tích sẽ sử dụng')).toBeInTheDocument();
    expect(screen.getByText('Phân tích doanh nghiệp')).toBeInTheDocument();

    // Unselected capabilities must NOT be displayed
    expect(screen.queryByText('Nhóm tham chiếu')).not.toBeInTheDocument();
    expect(screen.queryByText('Bối cảnh vĩ mô')).not.toBeInTheDocument();
  });

  it('correctly produces Company + Peer interpretation for comparative questions', async () => {
    const user = userEvent.setup();
    renderPage();

    const composer = await screen.findByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    await user.type(composer, 'TCB sinh lời tốt hơn hay kém nhóm so sánh?');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    // Interpreted state
    expect(await screen.findByText('Hệ thống hiểu yêu cầu')).toBeInTheDocument();
    expect(screen.getByText('Phân tích sẽ sử dụng')).toBeInTheDocument();

    // Both Company and Peer must be displayed
    expect(screen.getByText('Phân tích doanh nghiệp')).toBeInTheDocument();
    expect(screen.getByText('Nhóm tham chiếu')).toBeInTheDocument();

    // Macro is unselected and must NOT be displayed
    expect(screen.queryByText('Bối cảnh vĩ mô')).not.toBeInTheDocument();
  });

  it('transitions to Scope Mismatch state with clear recovery options when request is unsupported', async () => {
    const user = userEvent.setup();
    renderPage();

    const composer = await screen.findByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    await user.type(composer, 'So sánh chỉ số EPS năm 2023 của VCB.');

    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    // Mismatch state
    expect(
      await screen.findByText('Phạm vi yêu cầu chưa được hỗ trợ trong bộ dữ liệu này')
    ).toBeInTheDocument();
    expect(screen.getByText(/không có chỉ số EPS và chu kỳ năm 2023/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Chỉnh câu hỏi/ })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /Đổi nguồn dữ liệu/ })).toHaveLength(2);

    // Recovery action: clicking "Chỉnh câu hỏi" returns to composer
    await user.click(screen.getByRole('button', { name: /Chỉnh câu hỏi/ }));
    expect(screen.getByRole('heading', { name: 'Bạn muốn phân tích điều gì?' })).toBeInTheDocument();
  });

  it('opens the contextual DatasetSelectorSheet when clicking "Đổi nguồn dữ liệu"', async () => {
    const user = userEvent.setup();
    renderPage();

    const switchBtn = await screen.findByRole('button', { name: 'Đổi nguồn dữ liệu' });
    await user.click(switchBtn);

    // Dataset Selector Sheet
    expect(await screen.findByText('Nguồn dữ liệu phân tích')).toBeInTheDocument();
    expect(screen.getByText('Ngân hàng Việt Nam 2020–2023')).toBeInTheDocument();
    expect(screen.getByText('Thêm / kết nối nguồn dữ liệu')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Kết nối nguồn mới' })).toBeInTheDocument();
  });

  it('submits analysis request and confirms execution when analyst confirms interpreted scope', async () => {
    const user = userEvent.setup();
    const submitSpy = vi.spyOn(analysisService, 'submit').mockResolvedValue({
      status: 'CLIENT_VALIDATED',
      readyForBackendSubmission: true,
      requestId: 'test-req-123',
      message: 'Yêu cầu đã được xác nhận. Bắt đầu phân tích đa tác tử.'
    });

    renderPage();
    const composer = await screen.findByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    await user.type(composer, 'So sánh chất lượng tài sản của ACB và TCB năm 2024.');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    const confirmBtn = await screen.findByRole('button', { name: /Xác nhận & phân tích/ });
    await user.click(confirmBtn);

    expect(submitSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        objective: 'So sánh chất lượng tài sản của ACB và TCB năm 2024.',
        analysisTargetIds: ['acb', 'tcb'],
        capabilitySnapshotId: mockCapabilities.snapshotId,
        peerUniverseId: mockCapabilities.peerUniverse.id
      })
    );

    expect(await screen.findByText('Khởi tạo quy trình thành công')).toBeInTheDocument();
  });

  it('opens ScopeAdjustmentDrawer and allows fine-tuning business scope without manual specialist controls', async () => {
    const user = userEvent.setup();
    renderPage();

    const composer = await screen.findByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    await user.type(composer, 'So sánh chất lượng tài sản của ACB năm 2024.');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    const adjustBtn = await screen.findByRole('button', { name: /Chỉnh phạm vi/ });
    await user.click(adjustBtn);

    // Drawer is open
    expect(await screen.findByText('Chỉnh phạm vi phân tích')).toBeInTheDocument();
    expect(
      screen.getByText(/Công cụ hiệu chỉnh thứ cấp khi bạn muốn điều chỉnh kết quả bóc tách tự động/)
    ).toBeInTheDocument();

    // Critical constraint: NO manual specialist/capability controls or peer toggles in ScopeAdjustmentDrawer
    expect(screen.queryByText('Khả năng phân tích sử dụng')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Nhóm tham chiếu/ })).not.toBeInTheDocument();
    // Contextual read-only peer disclosure is present when plan includes Peer analysis
    expect(screen.getByText('Nhóm tham chiếu liên kết')).toBeInTheDocument();

    // Toggle TCB in business entities
    const tcbChip = screen.getByRole('button', { name: 'TCB' });
    await user.click(tcbChip);

    // Save changes
    const saveBtn = screen.getByRole('button', { name: 'Lưu thay đổi' });
    await user.click(saveBtn);

    // Inferred summary updated
    expect(screen.getByText(/ACB · TCB · Q1–Q4\/2024/)).toBeInTheDocument();
  });

  it('REGRESSION: preserves Macro + Company capabilities when analyst adjusts period in ScopeAdjustmentDrawer', async () => {
    const user = userEvent.setup();
    renderPage();

    const composer = await screen.findByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    await user.type(composer, 'Lãi suất điều hành liên quan thế nào đến TCB?');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    // Interpreted state contains Company + Macro
    expect(await screen.findByText('Phân tích doanh nghiệp')).toBeInTheDocument();
    expect(screen.getByText('Bối cảnh vĩ mô')).toBeInTheDocument();
    expect(screen.queryByText('Nhóm tham chiếu')).not.toBeInTheDocument();

    // Open ScopeAdjustmentDrawer and adjust period
    const adjustBtn = screen.getByRole('button', { name: /Chỉnh phạm vi/ });
    await user.click(adjustBtn);

    // Toggle a period (e.g. Q1/2024)
    const q1Chip = screen.getByRole('button', { name: /Q1\/2024/ });
    await user.click(q1Chip);

    // Save changes
    const saveBtn = screen.getByRole('button', { name: 'Lưu thay đổi' });
    await user.click(saveBtn);

    // Both Company and Macro MUST remain applicable
    expect(await screen.findByText('Phân tích doanh nghiệp')).toBeInTheDocument();
    expect(screen.getByText('Bối cảnh vĩ mô')).toBeInTheDocument();
    expect(screen.queryByText('Nhóm tham chiếu')).not.toBeInTheDocument();
  });

  it('REGRESSION: renders semantically consistent empty metric scope for Macro-only requests', async () => {
    const user = userEvent.setup();
    renderPage();

    const composer = await screen.findByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    await user.type(composer, 'Diễn biến chính sách tiền tệ và lãi suất điều hành trong năm 2024');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    expect(await screen.findByText('Hệ thống hiểu yêu cầu')).toBeInTheDocument();
    expect(screen.getByText('Toàn hệ thống · Q1–Q4/2024')).toBeInTheDocument();
    expect(screen.getByText('Không áp dụng (Bối cảnh vĩ mô)')).toBeInTheDocument();

    // Only Macro capability is active
    expect(screen.getByText('Bối cảnh vĩ mô')).toBeInTheDocument();
    expect(screen.queryByText('Phân tích doanh nghiệp')).not.toBeInTheDocument();
    expect(screen.queryByText('Nhóm tham chiếu')).not.toBeInTheDocument();
  });
});
