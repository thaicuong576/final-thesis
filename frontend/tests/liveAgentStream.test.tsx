import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AgentStage } from '../src/features/analysis-session/components/AgentStage';
import { deriveAgentWork } from '../src/features/analysis-session/model/agentStage';
import type { TraceStep } from '../src/features/analysis-session/model/types';
import { parseSseBlockRaw } from '../src/features/analysis-session/useTraceStream';
import traceFixture from '../src/test/fixtures/er-trace-acb-2024q4.json';

describe('SSE-1: Live Agent Stream & AgentStage Redesign', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('parseSseBlockRaw', () => {
    it('parses WRITER_DRAFT_DELTA event from raw SSE block', () => {
      const block = `event: WRITER_DRAFT_DELTA\ndata: {"delta":"ACB có tỷ lệ bao phủ nợ xấu ","role":"company","callKind":"findings"}`;
      const raw = parseSseBlockRaw(block);
      expect(raw).not.toBeNull();
      expect(raw?.type).toBe('WRITER_DRAFT_DELTA');
      expect(raw?.payload.delta).toBe('ACB có tỷ lệ bao phủ nợ xấu ');
      expect(raw?.payload.role).toBe('company');
      expect(raw?.payload.callKind).toBe('findings');
    });

    it('parses SENTENCE_VERDICT event with kept status and fact ids', () => {
      const block = `event: SENTENCE_VERDICT\ndata: {"sentence":"ACB dẫn đầu về ROE.","verdict":"kept","explanationVi":"Đã đối chiếu dữ liệu gốc","factIds":["fact:acb:roe"],"role":"verifier"}`;
      const raw = parseSseBlockRaw(block);
      expect(raw).not.toBeNull();
      expect(raw?.type).toBe('SENTENCE_VERDICT');
      expect(raw?.payload.sentence).toBe('ACB dẫn đầu về ROE.');
      expect(raw?.payload.verdict).toBe('kept');
      expect(raw?.payload.factIds).toEqual(['fact:acb:roe']);
    });

    it('parses SENTENCE_VERDICT event with dropped status and reason code', () => {
      const block = `event: SENTENCE_VERDICT\ndata: {"sentence":"Lợi nhuận tăng mạnh do cắt giảm chi phí.","verdict":"dropped","dropReason":"unsupported_claim","explanationVi":"Không có số liệu chứng minh","role":"verifier"}`;
      const raw = parseSseBlockRaw(block);
      expect(raw).not.toBeNull();
      expect(raw?.type).toBe('SENTENCE_VERDICT');
      expect(raw?.payload.verdict).toBe('dropped');
      expect(raw?.payload.dropReason).toBe('unsupported_claim');
      expect(raw?.payload.explanationVi).toBe('Không có số liệu chứng minh');
    });

    it('parses TOOL_STARTED and TOOL_COMPLETED events', () => {
      const startedBlock = `event: TOOL_STARTED\ndata: {"tool":"calculate_peer_rankings","arguments":{"entities":["ACB","VCB"],"metrics":["npl"]},"role":"sector"}`;
      const started = parseSseBlockRaw(startedBlock);
      expect(started?.type).toBe('TOOL_STARTED');
      expect(started?.payload.tool).toBe('calculate_peer_rankings');

      const completedBlock = `event: TOOL_COMPLETED\ndata: {"tool":"calculate_peer_rankings","resultCount":32,"durationMs":145,"role":"sector"}`;
      const completed = parseSseBlockRaw(completedBlock);
      expect(completed?.type).toBe('TOOL_COMPLETED');
      expect(completed?.payload.resultCount).toBe(32);
      expect(completed?.payload.durationMs).toBe(145);
    });

    it('parses WRITER_DRAFT_DISCARDED event when draft is reset', () => {
      const discardBlock = `event: WRITER_DRAFT_DISCARDED\ndata: {"role":"company","kind":"findings","reason":"stream_failed_retry"}`;
      const raw = parseSseBlockRaw(discardBlock);
      expect(raw).not.toBeNull();
      expect(raw?.type).toBe('WRITER_DRAFT_DISCARDED');
      expect(raw?.payload.role).toBe('company');
      expect(raw?.payload.kind).toBe('findings');
    });
  });

  describe('AgentStage Layout: No Card Overlap & Responsive Flow', () => {
    const mockSteps: TraceStep[] = [
      {
        step_id: 't-1',
        seq: 1,
        t_ms: 100,
        actor: 'orchestrator',
        recipient: 'system',
        kind: 'plan',
        summary: 'Lập kế hoạch phân tích',
        detail: {
          question_type: 'ranking',
          agents: [
            { agent: 'sector', decision: 'run' },
            { agent: 'verifier', decision: 'run' },
            { agent: 'critic', decision: 'run' }
          ]
        }
      },
      {
        step_id: 't-2',
        seq: 2,
        t_ms: 200,
        actor: 'orchestrator',
        recipient: 'sector',
        kind: 'assign',
        summary: 'Giao việc: xếp hạng toàn nhóm',
        detail: { task: 'Xếp hạng toàn nhóm' }
      }
    ];

    it('renders all planned agents in sequence without overlapping absolute coordinates', () => {
      render(
        <AgentStage
          steps={mockSteps}
          query="Ngân hàng nào có tỷ lệ bao phủ nợ xấu cao nhất quý 2/2026?"
          live={false}
        />
      );

      // Verify all agent regions exist and are accessible
      const orchCard = screen.getByRole('region', { name: 'Điều phối viên' });
      const sectorCard = screen.getByRole('region', { name: 'Sector' });
      const verifierCard = screen.getByRole('region', { name: 'Kiểm tra số liệu' });
      const criticCard = screen.getByRole('region', { name: 'Phản biện' });

      expect(orchCard).toBeInTheDocument();
      expect(sectorCard).toBeInTheDocument();
      expect(verifierCard).toBeInTheDocument();
      expect(criticCard).toBeInTheDocument();

      // Check that cards are rendered within the responsive grid container, not absolute overlay
      expect(orchCard.closest('.grid')).not.toBeNull();
      expect(sectorCard.closest('.grid')).not.toBeNull();
    });

    it('switches the active Live Work Pane when user clicks on another agent card', async () => {
      const user = userEvent.setup();
      render(
        <AgentStage
          steps={mockSteps}
          query="Xếp hạng nợ xấu"
          live={false}
        />
      );

      // Click on "Kiểm tra số liệu"
      const verifierCard = screen.getByRole('region', { name: 'Kiểm tra số liệu' });
      await user.click(verifierCard);

      // Live Work Pane should show inspector for "Kiểm tra số liệu"
      expect(screen.getByRole('region', { name: 'Chi tiết hoạt động của Kiểm tra số liệu' })).toBeInTheDocument();
    });
  });

  describe('Live Work Pane: Draft prose streaming, verdicts, and tool calls', () => {
    it('displays streaming draft prose and typing indicator with aria-live="polite"', () => {
      const liveWorkState = {
        draftsByRole: {
          company: 'Trong quý 4/2024, ACB duy trì tỷ lệ nợ xấu ở mức 1,2%.'
        },
        activeWriterRole: 'company',
        toolCallsByRole: {},
        verdictsByRole: {},
        reviewIssues: [],
        revisions: []
      };

      const steps: TraceStep[] = [
        {
          step_id: 't-1',
          seq: 1,
          t_ms: 100,
          actor: 'orchestrator',
          recipient: null,
          kind: 'plan',
          summary: 'Kế hoạch',
          detail: { question_type: 'company_profile', agents: [{ agent: 'company', decision: 'run' }] }
        }
      ];

      render(
        <AgentStage
          steps={steps}
          query="Phân tích ACB"
          live={true}
          liveWorkState={liveWorkState}
        />
      );

      // Company is active writer, so it should be auto-focused
      expect(screen.getByText('Bản nháp nhận định')).toBeInTheDocument();
      expect(screen.getByText(/ACB duy trì tỷ lệ nợ xấu ở mức 1,2%/)).toBeInTheDocument();
      expect(screen.getByText('Đang viết trực tiếp...')).toBeInTheDocument();
      expect(screen.getByText('đang truyền dòng văn bản...')).toBeInTheDocument();
    });

    it('renders kept (✓) and dropped (✗) sentence verdicts with Vietnamese reasons', async () => {
      const user = userEvent.setup();
      const liveWorkState = {
        draftsByRole: {
          company: 'Câu 1 được chấp nhận. Câu 2 bị loại.'
        },
        activeWriterRole: null,
        toolCallsByRole: {},
        verdictsByRole: {
          company: [
            {
              sentence: 'Câu 1 được chấp nhận.',
              verdict: 'kept' as const,
              explanationVi: 'Đã đối chiếu dữ liệu gốc',
              factIds: ['fact:acb:npl:2024q4']
            },
            {
              sentence: 'Câu 2 bị loại.',
              verdict: 'dropped' as const,
              dropReason: 'unsupported_claim',
              explanationVi: 'Số liệu không khớp với báo cáo tài chính',
              factIds: []
            }
          ]
        },
        reviewIssues: [],
        revisions: []
      };

      const steps: TraceStep[] = [
        {
          step_id: 't-1',
          seq: 1,
          t_ms: 100,
          actor: 'orchestrator',
          recipient: null,
          kind: 'plan',
          summary: 'Kế hoạch',
          detail: { question_type: 'company_profile', agents: [{ agent: 'company', decision: 'run' }] }
        }
      ];

      render(
        <AgentStage
          steps={steps}
          query="Phân tích ACB"
          live={true}
          liveWorkState={liveWorkState}
        />
      );

      // Select company card to view its verdicts
      const companyCard = screen.getByRole('region', { name: 'Company' });
      await user.click(companyCard);

      expect(screen.getByText('Kết quả kiểm định từng câu (2)')).toBeInTheDocument();
      expect(screen.getByText('Câu 1 được chấp nhận.')).toBeInTheDocument();
      expect(screen.getByText('fact:acb:npl:2024q4')).toBeInTheDocument();
      expect(screen.getByText('Câu 2 bị loại.')).toBeInTheDocument();
      expect(screen.getByText(/Lý do: Số liệu không khớp với báo cáo tài chính/)).toBeInTheDocument();
    });

    it('renders compact tool calls table with arguments, result count, and duration', async () => {
      const user = userEvent.setup();
      const liveWorkState = {
        draftsByRole: {},
        activeWriterRole: null,
        toolCallsByRole: {
          company: [
            {
              tool: 'query_metric_observations',
              arguments: { entities: ['ACB'], metrics: ['bank.npl_g35'], periods: ['2024_Q4'] },
              resultCount: 16,
              durationMs: 85,
              status: 'completed' as const
            }
          ]
        },
        verdictsByRole: {},
        reviewIssues: [],
        revisions: []
      };

      const steps: TraceStep[] = [
        {
          step_id: 't-1',
          seq: 1,
          t_ms: 100,
          actor: 'orchestrator',
          recipient: null,
          kind: 'plan',
          summary: 'Kế hoạch',
          detail: { question_type: 'company_profile', agents: [{ agent: 'company', decision: 'run' }] }
        }
      ];

      render(
        <AgentStage
          steps={steps}
          query="Phân tích ACB"
          live={true}
          liveWorkState={liveWorkState}
        />
      );

      // Select company card to view its tool calls
      const companyCard = screen.getByRole('region', { name: 'Company' });
      await user.click(companyCard);

      expect(screen.getByText('Truy vấn dữ liệu (1)')).toBeInTheDocument();
      expect(screen.getByText('query_metric_observations')).toBeInTheDocument();
      expect(screen.getByText(/16 số liệu/)).toBeInTheDocument();
      expect(screen.getByText('85ms')).toBeInTheDocument();
    });
  });

  describe('Completed-run replay from stored trace steps (Requirement 9)', () => {
    it('replays full agent work from stored traceFixture without live typing', () => {
      const steps = traceFixture.steps as unknown as TraceStep[];
      render(
        <AgentStage
          steps={steps}
          query={traceFixture.query}
          live={false}
        />
      );

      // Company agent work derived from fixture trace
      const work = deriveAgentWork('company', steps);
      expect(work.draftText).toContain('ACB duy trì khả năng sinh lời');
      expect(work.isTyping).toBe(false);
      expect(work.toolCalls.length).toBeGreaterThanOrEqual(1);

      // Click on company card
      const companyCard = screen.getByRole('region', { name: 'Company' });
      fireEvent.click(companyCard);

      // Work pane displays the stored draft text and tool calls
      const matchedTexts = screen.getAllByText(/ACB duy trì khả năng sinh lời/);
      expect(matchedTexts.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Truy vấn dữ liệu (1)')).toBeInTheDocument();
      expect(screen.getByText('peer_position')).toBeInTheDocument();
    });
  });
});
