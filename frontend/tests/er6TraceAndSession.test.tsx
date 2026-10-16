import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { TraceStep } from '../src/features/analysis-session/model/types';
import { OrchestratorBoard } from '../src/features/analysis-session/components/OrchestratorBoard';
import { ProcessTrace } from '../src/features/analysis-session/components/ProcessTrace';
import { parseTraceSseBlock } from '../src/features/analysis-session/useTraceStream';
import { ProcessLink } from '../src/features/equity-report/components/ProcessLink';
import { EquityReportProvider } from '../src/features/equity-report/components/EquityReportContext';
import type { AdaptiveReportResponse } from '../src/features/equity-report/model/types';
import type { AnalysisCapabilities } from '../src/entities/capability/model/types';
import traceFixture from '../src/test/fixtures/er-trace-acb-2024q4.json';

describe('ER-6 OrchestratorBoard', () => {
  const steps = traceFixture.steps as unknown as TraceStep[];

  it('renders only active agents (Chuyên viên doanh nghiệp, Chuyên viên ngành, Phản biện) and skips Chuyên viên vĩ mô', () => {
    render(<OrchestratorBoard steps={steps} query={traceFixture.query} />);

    // Top orchestrator card
    expect(screen.getByRole('region', { name: 'Điều phối viên' })).toBeInTheDocument();

    // Active child agent cards
    expect(screen.getByRole('region', { name: 'Chuyên viên doanh nghiệp' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Chuyên viên ngành' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Phản biện' })).toBeInTheDocument();

    // Macro was marked as skip in plan, so it MUST NOT be rendered
    expect(screen.queryByRole('region', { name: 'Chuyên viên vĩ mô' })).not.toBeInTheDocument();
  });

  it('marks engaged agents as "Xong" and unengaged agents as "Không dùng đến" at the end of the run', () => {
    render(<OrchestratorBoard steps={steps} query={traceFixture.query} />);

    const doneBadges = screen.getAllByText('Xong');
    // Orchestrator, Company, Phản biện = 3 "Xong" badges
    expect(doneBadges.length).toBeGreaterThanOrEqual(3);
    // Sector was never assigned a task or stepped in, so stays unengaged
    expect(screen.getAllByText('Không dùng đến').length).toBeGreaterThanOrEqual(1);
  });
});

describe('ER-6 ProcessTrace', () => {
  const steps = traceFixture.steps as unknown as TraceStep[];

  it('filters steps by actor when clicking an agent chip', async () => {
    const user = userEvent.setup();
    render(<ProcessTrace steps={steps} />);

    // Initially shows summary including all steps
    expect(screen.getByText(/3 agent · 1 vòng phản biện/)).toBeInTheDocument();

    // Click "Chuyên viên doanh nghiệp" chip in the filter group
    const filterGroup = screen.getByRole('group', { name: 'Lọc theo agent' });
    const companyChip = within(filterGroup).getByRole('button', { name: 'Chuyên viên doanh nghiệp' });
    await user.click(companyChip);

    // Only steps with Company as actor or recipient should be visible
    expect(screen.getByText(/Soạn thảo bản nháp nhận định ban đầu/)).toBeInTheDocument();
    // Orchestrator-only plan step shouldn't be in the list
    expect(screen.queryByText(/Lập kế hoạch phân tích hồ sơ doanh nghiệp ACB/)).not.toBeInTheDocument();
  });

  it('displays "Trước" and "Sau" text labels in revision step for accessibility', () => {
    render(<ProcessTrace steps={steps} />);

    // Step revision is expanded by default
    expect(screen.getByText(/Trước ·/)).toBeInTheDocument();
    expect(screen.getByText(/Sau ·/)).toBeInTheDocument();
    expect(screen.getAllByText(/Đệm bao phủ nợ xấu của ACB giảm\./).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Trong quý 4, đệm bao phủ nợ xấu của ACB giảm 2,51 điểm phần trăm/)).toBeInTheDocument();
  });

  it('is accessible and controllable via keyboard (Enter / Space)', () => {
    render(<ProcessTrace steps={steps} />);

    // Plan step is t-1
    const planHeader = screen.getByText(/Lập kế hoạch phân tích hồ sơ doanh nghiệp ACB/).closest('[role="button"]')!;
    expect(planHeader).toHaveAttribute('aria-expanded', 'false');

    // Press Enter to expand
    fireEvent.keyDown(planHeader, { key: 'Enter' });
    expect(planHeader).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Dạng câu hỏi:')).toBeInTheDocument();

    // Press Space to collapse
    fireEvent.keyDown(planHeader, { key: ' ' });
    expect(planHeader).toHaveAttribute('aria-expanded', 'false');
  });
});

describe('ER-6 useTraceStream parseTraceSseBlock', () => {
  it('parses TRACE_STEP event from standard SSE string format', () => {
    const sseBlock = `event: TRACE_STEP\ndata: {"step_id":"t-test","seq":1,"t_ms":200,"actor":"company","recipient":"orchestrator","kind":"tool_result","summary":"Fact extracted","detail":{}}`;
    const step = parseTraceSseBlock(sseBlock);

    expect(step).not.toBeNull();
    expect(step?.step_id).toBe('t-test');
    expect(step?.actor).toBe('company');
    expect(step?.kind).toBe('tool_result');
    expect(step?.summary).toBe('Fact extracted');
  });

  it('parses TRACE_STEP when wrapped in type/payload JSON', () => {
    const sseBlock = `data: {"type":"TRACE_STEP","payload":{"step_id":"t-payload","seq":2,"t_ms":400,"actor":"critic","recipient":"company","kind":"critique_issue","summary":"Review notice","detail":{}}}`;
    const step = parseTraceSseBlock(sseBlock);

    expect(step).not.toBeNull();
    expect(step?.step_id).toBe('t-payload');
    expect(step?.actor).toBe('critic');
  });

  it('parses legacy REPORT_READY event into report_ready step', () => {
    const sseBlock = `event: REPORT_READY\ndata: {"reportId":"rep-legacy-123","status":"completed"}`;
    const step = parseTraceSseBlock(sseBlock);

    expect(step).not.toBeNull();
    expect(step?.kind).toBe('report_ready');
    expect(step?.detail?.report_id).toBe('rep-legacy-123');
  });

  it('parses legacy RUN_BLOCKED event with mapped Vietnamese message', () => {
    const sseBlock = `event: RUN_BLOCKED\ndata: {"status":"error","reason":"unsupported_period","error":{"code":"unsupported_period","message":"Giai đoạn phân tích chưa được hỗ trợ.","suggestions":["Thử năm 2024"]}}`;
    const step = parseTraceSseBlock(sseBlock);

    expect(step).not.toBeNull();
    expect(step?.kind).toBe('blocked');
    expect(step?.detail?.code).toBe('unsupported_period');
    expect(step?.detail?.message).toBe('Kỳ bạn hỏi chưa có trong dữ liệu. Dữ liệu hiện có: Q1–Q4/2024.');
    expect(step?.detail?.suggestions).toEqual(['Thử năm 2024']);
  });

  it('parses legacy RUN_BLOCKED event with colon-separated reason ("unsupported_period: Period 2023_Q4 is not ...")', () => {
    const sseBlock = `event: RUN_BLOCKED\ndata: {"status":"error","reason":"unsupported_period: Period 2023_Q4 is not ..."}`;
    const step = parseTraceSseBlock(sseBlock);

    expect(step).not.toBeNull();
    expect(step?.kind).toBe('blocked');
    expect(step?.detail?.code).toBe('unsupported_period');
    expect(step?.detail?.message).toBe('Kỳ bạn hỏi chưa có trong dữ liệu. Dữ liệu hiện có: Q1–Q4/2024.');
    expect(step?.detail?.message).not.toBe('Hệ thống chưa trả lời được câu hỏi này.');
  });

  it('formats unsupported_metric and unsupported_entity messages using capabilities when provided', () => {
    const caps = {
      entities: [
        { id: 'ACB', ticker: 'ACB', name: 'Ngân hàng ACB' },
        { id: 'MBB', ticker: 'MBB', name: 'Ngân hàng MB' }
      ],
      periods: [
        { id: '2024_Q1', quarter: 1, year: 2024 },
        { id: '2024_Q4', quarter: 4, year: 2024 }
      ],
      metrics: [
        { id: 'bank.npl', acronym: 'NPL', label: 'Tỷ lệ nợ xấu', shortLabel: 'Nợ xấu', topicId: 'c' },
        { id: 'bank.roe', acronym: 'ROE', label: 'ROE', shortLabel: 'ROE', topicId: 'c' }
      ]
    } as unknown as AnalysisCapabilities;

    const blockPeriod = `event: RUN_BLOCKED\ndata: {"status":"error","reason":"unsupported_period"}`;
    const stepPeriod = parseTraceSseBlock(blockPeriod, caps);
    expect(stepPeriod?.detail?.message).toBe('Kỳ bạn hỏi chưa có trong dữ liệu. Dữ liệu hiện có: Q1–Q4/2024.');

    const blockMetric = `event: RUN_BLOCKED\ndata: {"status":"error","reason":"unsupported_metric"}`;
    const stepMetric = parseTraceSseBlock(blockMetric, caps);
    expect(stepMetric?.detail?.message).toBe('Chỉ tiêu bạn hỏi chưa có trong dữ liệu. Dữ liệu hiện có: Nợ xấu, ROE.');

    const blockEntity = `event: RUN_BLOCKED\ndata: {"status":"error","reason":"unsupported_entity"}`;
    const stepEntity = parseTraceSseBlock(blockEntity, caps);
    expect(stepEntity?.detail?.message).toBe('Ngân hàng bạn hỏi chưa có trong dữ liệu. Dữ liệu hiện có: ACB, MBB.');
  });

  it('silently ignores unrelated legacy events without throwing', () => {
    const legacyBlock1 = `event: PLANNING_STARTED\ndata: {"type":"PLANNING_STARTED","payload":{"message":"Starting..."}}`;
    const legacyBlock2 = `event: ping\ndata: {}`;
    const emptyBlock = ``;

    expect(parseTraceSseBlock(legacyBlock1)).toBeNull();
    expect(parseTraceSseBlock(legacyBlock2)).toBeNull();
    expect(parseTraceSseBlock(emptyBlock)).toBeNull();
  });
});

describe('ER-6 ProcessLink', () => {
  const dummyReport: AdaptiveReportResponse = {
    report_id: 'rep-test-link',
    report_version: 'adaptive_v1',
    status: 'completed',
    analysis_type: 'company_profile',
    title: 'Hồ sơ ngân hàng ACB',
    issuer: { ticker: 'ACB', name: 'Ngân hàng ACB' },
    period: '2024_Q4',
    blocks: [],
    facts: [],
    datasets: []
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders initial label without hardcoded 3/2/38 numbers and shows trace in Sheet on click', async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/runs/rep-test-link/trace')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            steps: traceFixture.steps,
            duration_ms: 12000
          })
        } as Response);
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response);
    });

    render(
      <EquityReportProvider report={dummyReport}>
        <ProcessLink />
      </EquityReportProvider>
    );

    // Initial label before trace loads or while loading
    expect(screen.getByRole('button', { name: /Xem quá trình phân tích/i })).toBeInTheDocument();

    // After fetch resolves, dynamic metadata is shown
    expect(
      await screen.findByRole('button', {
        name: /Xem quá trình phân tích · 3 agent · 1 vòng phản biện/i
      })
    ).toBeInTheDocument();

    // Clicking button opens Sheet
    await user.click(screen.getByRole('button', { name: /Xem quá trình phân tích/i }));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getAllByText('Quá trình phân tích').length).toBeGreaterThanOrEqual(1);
  });

  it('displays fallback message when trace API returns 404 or fails', async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404
    } as Response);

    render(
      <EquityReportProvider report={dummyReport}>
        <ProcessLink />
      </EquityReportProvider>
    );

    // Click link to open sheet
    await user.click(screen.getByRole('button', { name: /Xem quá trình phân tích/i }));

    // Shows 404 fallback message
    expect(await screen.findByText('Chưa có dữ liệu quá trình cho báo cáo này.')).toBeInTheDocument();
  });
});
