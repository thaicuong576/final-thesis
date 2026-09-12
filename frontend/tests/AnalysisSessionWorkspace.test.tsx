import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CreateAnalysisPage } from '../src/pages/create-analysis/CreateAnalysisPage';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';
import { parseAnalysisQuestion } from '../src/features/analysis-composer';
import {
  AnalysisSessionWorkspace,
  createAnalysisSession
} from '../src/features/analysis-session';

function renderPage(initialEntry = '/analysis') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <QueryClientProvider client={client}>
        <CreateAnalysisPage />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

describe('Analysis Session / Orchestrator Workspace (Screen 2 Clean-Room)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('Scenario A: Company-only run renders only Company invocation, omitting inactive specialists', async () => {
    const question = 'ROE của TCB thay đổi thế nào trong năm 2024?';
    const parsed = parseAnalysisQuestion(question, mockCapabilities);
    const session = createAnalysisSession(parsed, mockCapabilities);

    render(<AnalysisSessionWorkspace session={session} />);

    // 1. Session Context Bar (Layer A)
    expect(screen.getByText('Phiên phân tích đa tác tử')).toBeInTheDocument();
    expect(screen.getByText('Ngân hàng Việt Nam 2024')).toBeInTheDocument();
    expect(screen.getByText('TCB · Q1–Q4/2024 · ROE', { exact: true })).toBeInTheDocument();
    expect(screen.getByText('Sẵn sàng tạo báo cáo')).toBeInTheDocument();

    // 2. Orchestrator Thread (Layer B)
    expect(screen.getByText('Trao đổi với Điều phối viên')).toBeInTheDocument();
    expect(screen.getByText(question)).toBeInTheDocument();
    expect(screen.getAllByText('Điều phối').length).toBeGreaterThan(0);
    expect(screen.getByText(/Đã giao 1 nhiệm vụ chuyên môn/)).toBeInTheDocument();

    // 3. Specialist Invocations (Layer C) - Strictly only Company
    expect(screen.getByText('Chuyên môn đang thực hiện')).toBeInTheDocument();
    expect(screen.getByText('1 chuyên môn')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem chi tiết phiên Phân tích doanh nghiệp/ })).toBeInTheDocument();
    expect(screen.getByText('Đã hoàn tất')).toBeInTheDocument();

    // 4. Inactive specialists (Peer & Macro) must NOT have any DOM presence
    expect(screen.queryByText('Nhóm tham chiếu')).not.toBeInTheDocument();
    expect(screen.queryByText('Bối cảnh vĩ mô')).not.toBeInTheDocument();

    // 5. Synthesis & Report Ready (Layer E)
    expect(screen.getByText('Báo cáo phân tích đã sẵn sàng')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem báo cáo phân tích/ })).toBeInTheDocument();
  });

  it('Scenario B: Company + Peer run renders both active specialists and omits Macro', async () => {
    const question = 'TCB sinh lời tốt hơn hay kém nhóm so sánh trong năm 2024?';
    const parsed = parseAnalysisQuestion(question, mockCapabilities);
    const session = createAnalysisSession(parsed, mockCapabilities);

    render(<AnalysisSessionWorkspace session={session} />);

    // 1. Context Bar
    expect(screen.getByText('TCB · Q1–Q4/2024 · ROA · ROE', { exact: true })).toBeInTheDocument();

    // 2. Orchestrator message
    expect(screen.getByText(/Đã giao 2 nhiệm vụ chuyên môn/)).toBeInTheDocument();

    // 3. Both Company and Peer specialists are rendered
    expect(screen.getByText('2 chuyên môn')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem chi tiết phiên Phân tích doanh nghiệp/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem chi tiết phiên Nhóm tham chiếu/ })).toBeInTheDocument();

    // 4. Inactive specialist Macro must NOT exist in the DOM
    expect(screen.queryByText('Bối cảnh vĩ mô')).not.toBeInTheDocument();
  });

  it('Scenario C: Targeted Revision renders affected specialist as Revising and unaffected specialist as Completed', async () => {
    const question = 'TCB sinh lời tốt hơn hay kém nhóm so sánh trong năm 2024?';
    const parsed = parseAnalysisQuestion(question, mockCapabilities);
    // Targeted revision on Peer
    const session = createAnalysisSession(parsed, mockCapabilities, { withTargetedRevision: true });

    render(<AnalysisSessionWorkspace session={session} />);

    // 1. Orchestrator status indicates targeted revision
    expect(screen.getByText('Đang hiệu chỉnh chuyên môn liên quan')).toBeInTheDocument();
    expect(
      screen.getByText(/Tôi phát hiện một benchmark trong kết quả đối sánh chưa cùng kỳ/)
    ).toBeInTheDocument();

    // 2. Unaffected Company specialist is Completed
    const companyCard = screen.getByRole('button', { name: /Xem chi tiết phiên Phân tích doanh nghiệp/ });
    expect(within(companyCard).getByText('Đã hoàn tất')).toBeInTheDocument();

    // 3. Affected Peer specialist is in Revising state
    const peerCard = screen.getByRole('button', { name: /Xem chi tiết phiên Nhóm tham chiếu/ });
    expect(within(peerCard).getByText(/Đang hiệu chỉnh · vòng 1\/2/)).toBeInTheDocument();

    // 4. Macro still does not exist
    expect(screen.queryByText('Bối cảnh vĩ mô')).not.toBeInTheDocument();
  });

  it('Scenario D: Macro + Company run renders Macro and Company, omitting Peer', async () => {
    const question = 'Lãi suất điều hành liên quan thế nào đến TCB trong năm 2024?';
    const parsed = parseAnalysisQuestion(question, mockCapabilities);
    const session = createAnalysisSession(parsed, mockCapabilities);

    render(<AnalysisSessionWorkspace session={session} />);

    // 1. Both Macro and Company rendered
    expect(screen.getByText('2 chuyên môn')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem chi tiết phiên Phân tích doanh nghiệp/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem chi tiết phiên Bối cảnh vĩ mô/ })).toBeInTheDocument();

    // 2. Peer is absent
    expect(screen.queryByText('Nhóm tham chiếu')).not.toBeInTheDocument();
  });

  it('Sheet Inspection: clicking a specialist card opens slide-over sheet with activities, artifact, and review details', async () => {
    const user = userEvent.setup();
    const question = 'TCB sinh lời tốt hơn hay kém nhóm so sánh trong năm 2024?';
    const parsed = parseAnalysisQuestion(question, mockCapabilities);
    const session = createAnalysisSession(parsed, mockCapabilities, { withTargetedRevision: true });

    render(<AnalysisSessionWorkspace session={session} />);

    // Click on Peer card
    const peerCard = screen.getByRole('button', { name: /Xem chi tiết phiên Nhóm tham chiếu/ });
    await user.click(peerCard);

    // Sheet is opened
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText('Nhóm tham chiếu')).toBeInTheDocument();
    expect(within(dialog).getByText('Nhiệm vụ được phân công')).toBeInTheDocument();

    // Review feedback block is visible
    expect(within(dialog).getByText('Đánh giá từ Điều phối viên')).toBeInTheDocument();
    expect(within(dialog).getByText('Yêu cầu hiệu chỉnh')).toBeInTheDocument();
    expect(
      within(dialog).getByText(/Benchmark của nhận định thứ hai chưa cùng kỳ \(Q3 thay vì Q4\)/)
    ).toBeInTheDocument();

    // Revision round details are visible
    expect(within(dialog).getByText('Quá trình hiệu chỉnh có chủ đích')).toBeInTheDocument();
    expect(within(dialog).getByText('Vòng 1 / 2')).toBeInTheDocument();
    expect(within(dialog).getByText('Đồng bộ lại benchmark quý 4 cho nhóm tham chiếu')).toBeInTheDocument();

    // Observable activity timeline is visible
    expect(within(dialog).getByText('Hoạt động quan sát được')).toBeInTheDocument();
    expect(within(dialog).getByText(/Đang truy xuất lại dữ liệu benchmark Q4/)).toBeInTheDocument();

    // Dismiss sheet
    const closeBtn = within(dialog).getByRole('button', { name: 'Đóng' });
    await user.click(closeBtn);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('seamlessly transitions from Screen 1 confirmation into Screen 2 Analysis Session', async () => {
    const user = userEvent.setup();
    renderPage();

    const composer = await screen.findByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    await user.type(composer, 'ROE của TCB thay đổi thế nào trong năm 2024?');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    // Screen 1 Interpreted state
    const confirmBtn = await screen.findByRole('button', { name: /Xác nhận & phân tích/ });
    await user.click(confirmBtn);

    // Screen 2 Session workspace is now rendered
    expect(await screen.findByText('Phiên phân tích đa tác tử')).toBeInTheDocument();
    expect(screen.getByText('Trao đổi với Điều phối viên')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem chi tiết phiên Phân tích doanh nghiệp/ })).toBeInTheDocument();
    expect(screen.queryByText('Nhóm tham chiếu')).not.toBeInTheDocument();
  });

  it('URL scenario parameter directly launches corresponding session scenario', async () => {
    renderPage('/analysis?scenario=TARGETED_REVISION');

    // Should immediately mount the targeted revision session
    expect(await screen.findByText('Phiên phân tích đa tác tử')).toBeInTheDocument();
    expect(screen.getByText(/Đang hiệu chỉnh chuyên môn liên quan/)).toBeInTheDocument();
    expect(screen.getByText(/Đang hiệu chỉnh · vòng 1\/2/)).toBeInTheDocument();
  });

  it('guardrail verification: UI contains no raw technical event enum names or private reasoning dumps', () => {
    const question = 'TCB sinh lời tốt hơn hay kém nhóm so sánh trong năm 2024?';
    const parsed = parseAnalysisQuestion(question, mockCapabilities);
    const session = createAnalysisSession(parsed, mockCapabilities, { withTargetedRevision: true });

    render(<AnalysisSessionWorkspace session={session} />);

    // Assert no technical enum names leak to user interface
    expect(screen.queryByText(/AGENT_EXECUTION/)).not.toBeInTheDocument();
    expect(screen.queryByText(/TOOL_CALL/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ORCHESTRATOR_DISPATCH/)).not.toBeInTheDocument();
    expect(screen.queryByText(/LLM_STREAM/)).not.toBeInTheDocument();
    expect(screen.queryByText(/THINKING_PROCESS/)).not.toBeInTheDocument();
  });
});
