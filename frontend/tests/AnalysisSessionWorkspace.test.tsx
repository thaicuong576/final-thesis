import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CreateAnalysisPage } from '../src/pages/create-analysis/CreateAnalysisPage';
import {
  AnalysisSessionWorkspace,
  projectAnalysisSession,
  mockCompanyOnlyEvents,
  mockCompanyPeerEvents,
  mockTargetedRevisionEvents,
  mockMacroCompanyEvents
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

describe('Event-Driven Orchestrator Analysis Session (Screen 2 Clean-Room)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // A. PROJECTOR DETERMINISM
  it('Projector determinism: same event sequence always yields strictly identical view model', () => {
    const vm1 = projectAnalysisSession(mockTargetedRevisionEvents);
    const vm2 = projectAnalysisSession(mockTargetedRevisionEvents);

    expect(vm1).toEqual(vm2);
    expect(vm1.currentPhase).toBe('READY_FOR_REPORT');
    expect(vm1.reportReady).toBe(true);
    expect(vm1.invocations).toHaveLength(2);
  });

  // B. PREFIX PROPERTY: Intermediate states
  it('Prefix property: events.slice(0, n) derives expected intermediate states', () => {
    // Step 2: Planning started, no specialists yet
    const planningState = projectAnalysisSession(mockTargetedRevisionEvents.slice(0, 2));
    expect(planningState.currentPhase).toBe('PLANNING');
    expect(planningState.invocations).toHaveLength(0);
    expect(planningState.reportReady).toBe(false);

    // Step 4: Company invoked, Peer not yet invoked
    const companyInvokedState = projectAnalysisSession(mockTargetedRevisionEvents.slice(0, 4));
    expect(companyInvokedState.invocations).toHaveLength(1);
    expect(companyInvokedState.specialistSessions['inv-company']).toBeDefined();
    expect(companyInvokedState.specialistSessions['inv-peer']).toBeUndefined();

    // Step 5: Both Company and Peer invoked
    const bothInvokedState = projectAnalysisSession(mockTargetedRevisionEvents.slice(0, 5));
    expect(bothInvokedState.invocations).toHaveLength(2);
    expect(bothInvokedState.specialistSessions['inv-peer']).toBeDefined();
  });

  // C. COMPANY-ONLY: Chronology and Query-Adaptive Omission
  it('Scenario A: Company-only question renders Company inline, omitting inactive specialists', () => {
    const viewModel = projectAnalysisSession(mockCompanyOnlyEvents);
    render(<AnalysisSessionWorkspace viewModel={viewModel} />);

    // 1. Context Bar
    expect(screen.getByText('Phiên phân tích đa tác tử')).toBeInTheDocument();
    expect(screen.getByText('Ngân hàng Việt Nam 2024')).toBeInTheDocument();
    expect(screen.getByText('TCB · Q1–Q4/2024 · ROE')).toBeInTheDocument();

    // 2. Thread timeline shows User question and Orchestrator message
    expect(screen.getByText('Tiến trình làm việc của Điều phối viên')).toBeInTheDocument();
    expect(screen.getByText('ROE của TCB thay đổi thế nào trong năm 2024?')).toBeInTheDocument();
    expect(screen.getAllByText('Điều phối').length).toBeGreaterThan(0);

    // 3. Inline Specialist Invocation: Company ONLY
    const companyCard = screen.getByRole('button', {
      name: /Xem chi tiết phiên Phân tích doanh nghiệp/
    });
    expect(within(companyCard).getByText('Đã hoàn tất')).toBeInTheDocument();

    // 4. Inactive specialists (Peer and Macro) must NOT exist in the DOM
    expect(screen.queryByText('Nhóm tham chiếu')).not.toBeInTheDocument();
    expect(screen.queryByText('Bối cảnh vĩ mô')).not.toBeInTheDocument();

    // 5. Report CTA is visible because REPORT_READY event was emitted
    expect(screen.getByText('Báo cáo phân tích đã sẵn sàng')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem báo cáo phân tích/ })).toBeInTheDocument();
  });

  // D. COMPANY + PEER: Both appear inline, Macro never appears
  it('Scenario B: Company + Peer question renders both specialists inline, Macro never appears', () => {
    const viewModel = projectAnalysisSession(mockCompanyPeerEvents);
    render(<AnalysisSessionWorkspace viewModel={viewModel} />);

    // Both specialists are rendered inline
    expect(screen.getByRole('button', { name: /Xem chi tiết phiên Phân tích doanh nghiệp/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem chi tiết phiên Nhóm tham chiếu/ })).toBeInTheDocument();

    // Macro must never appear
    expect(screen.queryByText('Bối cảnh vĩ mô')).not.toBeInTheDocument();
  });

  // D2. MACRO + COMPANY: Both appear inline, Peer never appears
  it('Scenario D: Macro + Company question renders Macro and Company inline, Peer never appears', () => {
    const viewModel = projectAnalysisSession(mockMacroCompanyEvents);
    render(<AnalysisSessionWorkspace viewModel={viewModel} />);

    // Both specialists are rendered inline
    expect(screen.getByRole('button', { name: /Xem chi tiết phiên Phân tích doanh nghiệp/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem chi tiết phiên Bối cảnh vĩ mô/ })).toBeInTheDocument();

    // Peer must never appear
    expect(screen.queryByText('Nhóm tham chiếu')).not.toBeInTheDocument();
  });

  // E. TARGETED REVISION: Peer revising, Company completed
  it('Scenario C: Targeted Revision renders Peer as Revising while Company remains Completed', () => {
    // Cut off events right after REVISION_REQUESTED (event 16 in targetedRevisionEvents)
    const revisionEvents = mockTargetedRevisionEvents.slice(0, 16);
    const viewModel = projectAnalysisSession(revisionEvents);

    render(<AnalysisSessionWorkspace viewModel={viewModel} />);

    // Orchestrator status indicates targeted revision
    expect(screen.getByText('Đang hiệu chỉnh chuyên môn liên quan')).toBeInTheDocument();
    expect(
      screen.getByText(/Tôi phát hiện một benchmark trong kết quả đối sánh chưa cùng kỳ/)
    ).toBeInTheDocument();

    // Unaffected Company specialist remains completed
    const companyCard = screen.getByRole('button', { name: /Xem chi tiết phiên Phân tích doanh nghiệp/ });
    expect(within(companyCard).getByText('Đã hoàn tất')).toBeInTheDocument();

    // Affected Peer specialist is in Revising state
    const peerCard = screen.getByRole('button', { name: /Xem chi tiết phiên Nhóm tham chiếu/ });
    expect(within(peerCard).getByText(/Đang hiệu chỉnh · vòng 1\/2/)).toBeInTheDocument();

    // Macro never appears
    expect(screen.queryByText('Bối cảnh vĩ mô')).not.toBeInTheDocument();
  });

  // F. REVISION HISTORY IN SPECIALIST SHEET
  it('Specialist Sheet reconstructs complete revision history from events', async () => {
    const user = userEvent.setup();
    // Full sequence with completed revision
    const viewModel = projectAnalysisSession(mockTargetedRevisionEvents);

    render(<AnalysisSessionWorkspace viewModel={viewModel} />);

    // Click on Peer card to open sheet
    const peerCard = screen.getByRole('button', { name: /Xem chi tiết phiên Nhóm tham chiếu/ });
    await user.click(peerCard);

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText('Nhóm tham chiếu')).toBeInTheDocument();
    expect(within(dialog).getByText('Nhiệm vụ được phân công')).toBeInTheDocument();

    // Initial artifact (v1)
    expect(within(dialog).getByText('Kết quả ban đầu (v1)')).toBeInTheDocument();
    expect(within(dialog).getByText(/3 nhận định đối sánh v1/)).toBeInTheDocument();

    // Review feedback from Orchestrator
    expect(within(dialog).getByText('Đánh giá từ Điều phối viên')).toBeInTheDocument();
    expect(
      within(dialog).getByText(/Benchmark của nhận định thứ hai chưa cùng kỳ \(Q3 thay vì Q4\)/)
    ).toBeInTheDocument();

    // Targeted revision round
    expect(within(dialog).getByText('Quá trình hiệu chỉnh có chủ đích')).toBeInTheDocument();
    expect(within(dialog).getByText('Vòng 1 / 2')).toBeInTheDocument();
    expect(within(dialog).getByText('Đồng bộ lại benchmark quý 4 cho nhóm tham chiếu')).toBeInTheDocument();

    // Revised artifact (v2)
    expect(within(dialog).getByText('Kết quả sau hiệu chỉnh (v2)')).toBeInTheDocument();
    expect(within(dialog).getByText(/3 nhận định đối sánh chuẩn hóa/)).toBeInTheDocument();

    // Observable activity timeline
    expect(within(dialog).getByText('Hoạt động quan sát được')).toBeInTheDocument();

    // Dismiss sheet
    const closeBtn = within(dialog).getByRole('button', { name: 'Đóng' });
    await user.click(closeBtn);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  // G. REPORT READY
  it('Report CTA appears only when REPORT_READY event is present in the stream', () => {
    // Prefix without REPORT_READY
    const beforeReady = projectAnalysisSession(mockCompanyOnlyEvents.slice(0, 11));
    const { rerender } = render(<AnalysisSessionWorkspace viewModel={beforeReady} />);
    expect(screen.queryByText('Báo cáo phân tích đã sẵn sàng')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Xem báo cáo phân tích/ })).not.toBeInTheDocument();

    // Full stream with REPORT_READY
    const afterReady = projectAnalysisSession(mockCompanyOnlyEvents);
    rerender(<AnalysisSessionWorkspace viewModel={afterReady} />);
    expect(screen.getByText('Báo cáo phân tích đã sẵn sàng')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem báo cáo phân tích/ })).toBeInTheDocument();
  });

  // H. AUDIT URL PARAMETERS: mockScenario & mockStep
  it('Audit URL parameters: /analysis?mockScenario=targeted-revision&mockStep=16 renders deterministic prefix', async () => {
    renderPage('/analysis?mockScenario=targeted-revision&mockStep=16');

    // Should mount session at step 16 (Peer revising, Company completed)
    expect(await screen.findByText('Phiên phân tích đa tác tử')).toBeInTheDocument();
    expect(screen.getByText(/Đang hiệu chỉnh chuyên môn liên quan/)).toBeInTheDocument();
    expect(screen.getByText(/Đang hiệu chỉnh · vòng 1\/2/)).toBeInTheDocument();
  });

  // I. GUARDRAIL VERIFICATION: NO RAW ENUMS IN NORMAL UI
  it('Guardrail verification: UI contains no raw technical event enum names or private reasoning dumps', () => {
    const viewModel = projectAnalysisSession(mockTargetedRevisionEvents);
    render(<AnalysisSessionWorkspace viewModel={viewModel} />);

    expect(screen.queryByText(/USER_REQUEST_CONFIRMED/)).not.toBeInTheDocument();
    expect(screen.queryByText(/SPECIALIST_INVOKED/)).not.toBeInTheDocument();
    expect(screen.queryByText(/SPECIALIST_STARTED/)).not.toBeInTheDocument();
    expect(screen.queryByText(/REVISION_REQUESTED/)).not.toBeInTheDocument();
    expect(screen.queryByText(/REPORT_READY/)).not.toBeInTheDocument();
    expect(screen.queryByText(/THINKING_PROCESS/)).not.toBeInTheDocument();
  });
});
