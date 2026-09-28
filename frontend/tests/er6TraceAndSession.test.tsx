import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { TraceStep } from '../src/features/analysis-session/model/types';
import { OrchestratorBoard } from '../src/features/analysis-session/components/OrchestratorBoard';
import { ProcessTrace } from '../src/features/analysis-session/components/ProcessTrace';
import { parseTraceSseBlock } from '../src/features/analysis-session/useTraceStream';
import traceFixture from '../src/test/fixtures/er-trace-acb-2024q4.json';

describe('ER-6 OrchestratorBoard', () => {
  const steps = traceFixture.steps as unknown as TraceStep[];

  it('renders only active agents (Company, Sector, Phản biện) and skips Macro', () => {
    render(<OrchestratorBoard steps={steps} query={traceFixture.query} />);

    // Top orchestrator card
    expect(screen.getByRole('region', { name: 'Điều phối viên' })).toBeInTheDocument();

    // Active child agent cards
    expect(screen.getByRole('region', { name: 'Company' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Sector' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Phản biện' })).toBeInTheDocument();

    // Macro was marked as skip in plan, so it MUST NOT be rendered
    expect(screen.queryByRole('region', { name: 'Macro' })).not.toBeInTheDocument();
  });

  it('marks all participating agents as "Xong" at the end of the run', () => {
    render(<OrchestratorBoard steps={steps} query={traceFixture.query} />);

    const doneBadges = screen.getAllByText('Xong');
    // Orchestrator, Company, Sector, Phản biện = 4 "Xong" badges
    expect(doneBadges.length).toBeGreaterThanOrEqual(4);
  });
});

describe('ER-6 ProcessTrace', () => {
  const steps = traceFixture.steps as unknown as TraceStep[];

  it('filters steps by actor when clicking an agent chip', async () => {
    const user = userEvent.setup();
    render(<ProcessTrace steps={steps} />);

    // Initially shows summary including all steps
    expect(screen.getByText(/3 agent · 1 vòng phản biện/)).toBeInTheDocument();

    // Click "Company" chip in the filter group
    const filterGroup = screen.getByRole('group', { name: 'Lọc theo agent' });
    const companyChip = within(filterGroup).getByRole('button', { name: 'Company' });
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

  it('silently ignores legacy events without throwing', () => {
    const legacyBlock1 = `event: PLANNING_STARTED\ndata: {"type":"PLANNING_STARTED","payload":{"message":"Starting..."}}`;
    const legacyBlock2 = `event: ping\ndata: {}`;
    const emptyBlock = ``;

    expect(parseTraceSseBlock(legacyBlock1)).toBeNull();
    expect(parseTraceSseBlock(legacyBlock2)).toBeNull();
    expect(parseTraceSseBlock(emptyBlock)).toBeNull();
  });
});
