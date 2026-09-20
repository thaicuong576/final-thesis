import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CreateAnalysisPage } from '../src/pages/create-analysis/CreateAnalysisPage';
import type { ParseResult } from '../src/features/analysis-composer';
import {
  AnalysisSessionWorkspace,
  projectAnalysisSession,
  buildMockEventsFromParseResult,
  getEventsForParseResult,
  mockCompanyOnlyEvents,
  mockCompanyPeerEvents,
  mockTargetedRevisionEvents,
  mockMacroCompanyEvents,
  type AnalysisSessionEvent
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

  // J. BLOCKER 1: NORMAL CONFIRMED RUN AUTOPLAYS SEQUENTIALLY
  it('Normal confirmed run starts in AUTOPLAY: initial session does not immediately show REPORT_READY and advances sequentially', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderPage('/analysis');

    const composer = await screen.findByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    await user.type(composer, 'ROE của TCB thay đổi thế nào trong năm 2024?');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    const confirmBtn = await screen.findByRole('button', { name: /Xác nhận & phân tích/ });
    await user.click(confirmBtn);

    // Initial session must be active, but at step 1 it does NOT show REPORT_READY CTA
    expect(await screen.findByText('Phiên phân tích đa tác tử')).toBeInTheDocument();
    expect(screen.queryByText('Báo cáo phân tích đã sẵn sàng')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Xem báo cáo phân tích/ })).not.toBeInTheDocument();

    // Advance timers across all emitted events
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15000);
    });

    // Now REPORT_READY has arrived sequentially
    expect(await screen.findByText('Báo cáo phân tích đã sẵn sàng')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xem báo cáo phân tích/ })).toBeInTheDocument();

    vi.useRealTimers();
  });

  // K. BLOCKER 2: NO VISIBLE SCENARIO SWITCHER IN NORMAL ANALYST UI
  it('Normal session UI never exposes demo scenario switcher controls to analysts', () => {
    const viewModel = projectAnalysisSession(mockCompanyOnlyEvents);
    render(<AnalysisSessionWorkspace viewModel={viewModel} />);

    expect(screen.queryByText('Kịch bản minh chứng:')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Doanh nghiệp (TCB)' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Doanh nghiệp + Peer' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Hiệu chỉnh có chủ đích' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Vĩ mô + Doanh nghiệp' })).not.toBeInTheDocument();
  });

  // L. BLOCKER 3: NO SILENT SCOPE SUBSTITUTION (ACB / NPL PRESERVATION)
  it('No silent scope substitution: arbitrary ParseResult preserves actual question, entity, and metric, omitting TCB/ROE', async () => {
    const user = userEvent.setup();
    renderPage('/analysis');

    const composer = await screen.findByPlaceholderText(/So sánh chất lượng tài sản của ACB, TCB và MBB/);
    await user.type(composer, 'Tỷ lệ nợ xấu của ACB thay đổi thế nào trong năm 2024?');
    await user.click(screen.getByRole('button', { name: /Bắt đầu phân tích/ }));

    const confirmBtn = await screen.findByRole('button', { name: /Xác nhận & phân tích/ });
    await user.click(confirmBtn);

    // Session displays ACB and NPL, preserving exact user question and scope
    expect(await screen.findByText(/Tỷ lệ nợ xấu của ACB thay đổi thế nào trong năm 2024\?/)).toBeInTheDocument();
    expect(screen.getByText(/ACB · Q1–Q4\/2024 · NPL/)).toBeInTheDocument();

    // TCB and ROE must NOT be present as substituted scope
    expect(screen.queryByText(/TCB · Q1–Q4\/2024 · ROE/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ROE của TCB thay đổi thế nào/)).not.toBeInTheDocument();
  });

  // M. BLOCKER 1 & 4: REMOVE FABRICATED FINANCIAL CLAIMS FROM MOCK ARTIFACTS
  it('Evidence discipline: mock artifacts contain no fabricated financial claims (NIM, operating cost, capital adequacy, 1.2x median, peer median, percentile 50, liquidity support)', () => {
    const fixtures = [
      ...mockCompanyOnlyEvents,
      ...mockCompanyPeerEvents,
      ...mockTargetedRevisionEvents,
      ...mockMacroCompanyEvents
    ];

    const prohibitedPatterns = [
      /\bNIM\b/i,
      /1\.2x/i,
      /chi phí hoạt động/i,
      /an toàn vốn/i,
      /trung vị/i,
      /phân vị/i,
      /hỗ trợ thanh khoản/i
    ];

    fixtures.forEach((event) => {
      const serialized = JSON.stringify(event);
      prohibitedPatterns.forEach((pattern) => {
        expect(serialized).not.toMatch(pattern);
      });
    });
  });

  // P. BLOCKER 2: EMPTY ANALYSIS PLAN MUST NOT PRODUCE REPORT_READY -> TERMINATES IN BLOCKED
  it('Empty AnalysisPlan produces 0 specialist invocations, emits RUN_BLOCKED, and terminates in BLOCKED without report synthesis', () => {
    const parseResult: ParseResult = {
      rawQuestion: 'Câu hỏi không gắn với chuyên môn nào',
      scope: {
        entities: [],
        periods: [],
        metrics: [],
        topicLabels: [],
        scopeSignature: 'Trống',
        analysisPlan: {
          selectedCapabilities: []
        }
      },
      mismatch: {
        isMismatch: false,
        availableCapabilitiesSummary: { periods: '', metrics: '', entities: '' }
      }
    };
    const events = buildMockEventsFromParseResult(parseResult);

    // 1. Zero specialist invocations
    const invokedEvents = events.filter((e) => e.type === 'SPECIALIST_INVOKED');
    expect(invokedEvents).toHaveLength(0);

    // 2. Terminal RUN_BLOCKED emitted, no REPORT_READY or synthesis events
    const blockedEvents = events.filter((e) => e.type === 'RUN_BLOCKED');
    expect(blockedEvents).toHaveLength(1);
    expect(blockedEvents[0].payload.reason).toBe(
      'Không có chuyên môn phân tích phù hợp với yêu cầu trong phạm vi dữ liệu hiện tại.'
    );
    expect(events.filter((e) => e.type === 'REVIEW_STARTED')).toHaveLength(0);
    expect(events.filter((e) => e.type === 'SYNTHESIS_STARTED')).toHaveLength(0);
    expect(events.filter((e) => e.type === 'SYNTHESIS_COMPLETED')).toHaveLength(0);
    expect(events.filter((e) => e.type === 'REPORT_READY')).toHaveLength(0);

    // 3. Projector derives BLOCKED phase and reportReady === false
    const vm = projectAnalysisSession(events);
    expect(vm.invocations).toHaveLength(0);
    expect(vm.currentPhase).toBe('BLOCKED');
    expect(vm.phaseLabel).toBe('Cần điều chỉnh yêu cầu');
    expect(vm.reportReady).toBe(false);

    // 4. UI renders normal orchestrator explanation, context badge, and NO report CTA
    render(<AnalysisSessionWorkspace viewModel={vm} />);
    expect(
      screen.getByText('Không có chuyên môn phân tích phù hợp với yêu cầu trong phạm vi dữ liệu hiện tại.')
    ).toBeInTheDocument();
    expect(screen.getByText('Cần điều chỉnh yêu cầu')).toBeInTheDocument();
    expect(screen.queryByText('Báo cáo phân tích đã sẵn sàng')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Xem báo cáo phân tích/ })).not.toBeInTheDocument();
  });

  // Q. BLOCKER 3: PREFIX PHASE PROGRESSION IN PROJECTOR
  it('Prefix phase progression: PLAN_CREATED -> DISPATCHING -> SPECIALIST_INVOKED -> DISPATCHING -> SPECIALIST_STARTED -> EXECUTING -> SPECIALIST_ACTIVITY -> EXECUTING -> REVIEW_STARTED -> REVIEWING', () => {
    const planCreatedIdx = mockCompanyOnlyEvents.findIndex((e) => e.type === 'PLAN_CREATED');
    const specialistInvokedIdx = mockCompanyOnlyEvents.findIndex((e) => e.type === 'SPECIALIST_INVOKED');
    const specialistStartedIdx = mockCompanyOnlyEvents.findIndex((e) => e.type === 'SPECIALIST_STARTED');
    const specialistActivityIdx = mockCompanyOnlyEvents.findIndex((e) => e.type === 'SPECIALIST_ACTIVITY');
    const reviewStartedIdx = mockCompanyOnlyEvents.findIndex((e) => e.type === 'REVIEW_STARTED');

    expect(projectAnalysisSession(mockCompanyOnlyEvents.slice(0, planCreatedIdx + 1)).currentPhase).toBe('DISPATCHING');
    expect(projectAnalysisSession(mockCompanyOnlyEvents.slice(0, specialistInvokedIdx + 1)).currentPhase).toBe('DISPATCHING');
    expect(projectAnalysisSession(mockCompanyOnlyEvents.slice(0, specialistStartedIdx + 1)).currentPhase).toBe('EXECUTING');
    expect(projectAnalysisSession(mockCompanyOnlyEvents.slice(0, specialistActivityIdx + 1)).currentPhase).toBe('EXECUTING');
    expect(projectAnalysisSession(mockCompanyOnlyEvents.slice(0, reviewStartedIdx + 1)).currentPhase).toBe('REVIEWING');
  });

  // R. BLOCKER 4: TARGETED REVISION DOES NOT SILENTLY OVERRIDE PARSERESULT
  it('Targeted revision does not silently override actual ParseResult in getEventsForParseResult', () => {
    const parseResult: ParseResult = {
      rawQuestion: 'Tỷ lệ nợ xấu của ACB thay đổi thế nào trong năm 2024?',
      scope: {
        entities: [{ id: 'acb', ticker: 'ACB', name: 'ACB' }],
        periods: [{ id: '2024-q1', quarter: 1, year: 2024 }],
        metrics: [{ id: 'npl', label: 'Nợ xấu', acronym: 'NPL', topicId: 'risk' }],
        topicLabels: ['Chất lượng tài sản'],
        scopeSignature: 'ACB · Q1/2024 · NPL',
        analysisPlan: {
          selectedCapabilities: [{ id: 'company', label: 'Phân tích doanh nghiệp', selected: true }]
        }
      },
      mismatch: {
        isMismatch: false,
        availableCapabilitiesSummary: { periods: '', metrics: '', entities: '' }
      }
    };
    const events = getEventsForParseResult(parseResult);
    expect(events[0].type).toBe('USER_REQUEST_CONFIRMED');
    if (events[0].type === 'USER_REQUEST_CONFIRMED') {
      expect(events[0].payload.rawQuestion).toBe('Tỷ lệ nợ xấu của ACB thay đổi thế nào trong năm 2024?');
    }
    // Ensure it is dynamic, not the hardcoded mockTargetedRevisionEvents (which uses TCB)
    expect(events.some((e) => JSON.stringify(e).includes('ACB'))).toBe(true);
    expect(events.some((e) => JSON.stringify(e).includes('TCB'))).toBe(false);
  });

  // N. BLOCKER 5: EXTENSIBLE SPECIALIST DECOUPLING WITH FALLBACK ICON
  it('Extensible specialist decoupling: non-standard specialistId renders with fallback icon', () => {
    const customEvents: AnalysisSessionEvent[] = [
      {
        eventId: 'evt-custom-01',
        sequence: 1,
        occurredAtMs: 0,
        type: 'USER_REQUEST_CONFIRMED',
        payload: {
          rawQuestion: 'Đánh giá rủi ro tín dụng của TCB',
          datasetName: 'Ngân hàng Việt Nam 2024',
          scopeSignature: 'TCB · 2024 · Risk'
        }
      },
      {
        eventId: 'evt-custom-02',
        sequence: 2,
        occurredAtMs: 500,
        type: 'SPECIALIST_INVOKED',
        payload: {
          invocationId: 'inv-risk',
          specialistId: 'risk_management', // Non-standard specialistId
          label: 'Quản trị rủi ro',
          assignment: 'Đánh giá khẩu vị rủi ro và các chỉ số an toàn tín dụng'
        }
      }
    ];

    const viewModel = projectAnalysisSession(customEvents);
    render(<AnalysisSessionWorkspace viewModel={viewModel} />);

    const customCard = screen.getByRole('button', {
      name: /Xem chi tiết phiên Quản trị rủi ro/
    });
    expect(customCard).toBeInTheDocument();
    expect(within(customCard).getByText('Quản trị rủi ro')).toBeInTheDocument();
  });

  // O. BLOCKER 5: SYNTHESIS LIFECYCLE COMPLETENESS
  it('Synthesis lifecycle: includes SYNTHESIS_STARTED, SYNTHESIS_COMPLETED, and REPORT_READY', () => {
    const types = mockCompanyOnlyEvents.map((e) => e.type);
    expect(types).toContain('SYNTHESIS_STARTED');
    expect(types).toContain('SYNTHESIS_COMPLETED');
    expect(types).toContain('REPORT_READY');
    expect(types.indexOf('SYNTHESIS_STARTED')).toBeLessThan(types.indexOf('SYNTHESIS_COMPLETED'));
    expect(types.indexOf('SYNTHESIS_COMPLETED')).toBeLessThan(types.indexOf('REPORT_READY'));
  });

  // =========================================================================
  // P. [THES-8] LIVE SSE STREAM & STATUS BADGE INTEGRATION
  // =========================================================================
  it('[THES-8] Displays Demo Mock Mode amber badge when running pre-baked events', () => {
    const viewModel = projectAnalysisSession(mockCompanyOnlyEvents);
    render(<AnalysisSessionWorkspace viewModel={viewModel} />);

    expect(screen.getByText('Demo Mock Mode')).toBeInTheDocument();
    expect(screen.queryByText('Live SSE Stream')).not.toBeInTheDocument();
  });

  it('[THES-8] Displays Live SSE Stream emerald badge when isLiveStream is active', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            'event: USER_REQUEST_CONFIRMED\ndata: {"eventId":"e1","sequence":1,"occurredAtMs":50,"type":"USER_REQUEST_CONFIRMED","payload":{"rawQuestion":"Live test","datasetName":"Ngân hàng Việt Nam 2024","scopeSignature":"ACB | Độc lập | 2024"}}\n\n'
          )
        );
      }
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body: stream
    } as unknown as Response);

    render(
      <MemoryRouter initialEntries={['/session?ticker=ACB&period=2024']}>
        <AnalysisSessionWorkspace isLiveStream={true} />
      </MemoryRouter>
    );

    expect(await screen.findByText('Live SSE Stream')).toBeInTheDocument();
  });

  it('[THES-8] Wires report navigation and passes generated report artifact to Screen 3', async () => {
    const user = userEvent.setup();
    const onViewReportMock = vi.fn();

    const mockReport = {
      report_id: 'rep-live-session-1',
      status: 'completed' as const,
      query: 'Live Query',
      target_ticker: 'ACB',
      peer_tickers: ['TCB'],
      period: '2024',
      analysis_plan: {
        plan_id: 'p1',
        query: 'Live Query',
        target_ticker: 'ACB',
        peer_tickers: ['TCB'],
        period: '2024',
        required_capabilities: ['company' as const],
        applicable_links: [],
        dataset_snapshot_id: 's1',
        rationale: '',
        known_limitations: []
      },
      macro_context: null,
      sector_benchmark: null,
      company_insights: [],
      cross_level_critique: [],
      atomic_claims: [],
      evidence_trail: [],
      revision_summary: {
        rounds_executed: 0,
        max_rounds: 2,
        status: 'passed' as const,
        reason: '',
        revised_capabilities: []
      },
      limitations: []
    };

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            'event: USER_REQUEST_CONFIRMED\ndata: {"eventId":"e1","sequence":1,"occurredAtMs":50,"type":"USER_REQUEST_CONFIRMED","payload":{"rawQuestion":"Live Query","datasetName":"Ngân hàng Việt Nam 2024","scopeSignature":"ACB | TCB | 2024"}}\n\n' +
            `event: REPORT_READY\ndata: {"eventId":"e2","sequence":2,"occurredAtMs":300,"type":"REPORT_READY","payload":{"message":"Hoàn tất báo cáo","reportId":"rep-live-session-1","report":${JSON.stringify(
              mockReport
            )}}}\n\n`
          )
        );
        controller.close();
      }
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body: stream
    } as unknown as Response);

    render(
      <MemoryRouter initialEntries={['/session']}>
        <AnalysisSessionWorkspace isLiveStream={true} onViewReport={onViewReportMock} />
      </MemoryRouter>
    );

    const reportBtn = await screen.findByRole('button', { name: /Xem báo cáo phân tích/i });
    expect(reportBtn).toBeInTheDocument();

    await user.click(reportBtn);
    expect(onViewReportMock).toHaveBeenCalledWith(
      expect.objectContaining({
        report_id: 'rep-live-session-1',
        target_ticker: 'ACB'
      })
    );
  });
});

