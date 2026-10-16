import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AgentStage } from '../src/features/analysis-session/components/AgentStage';
import type { TraceStep } from '../src/features/analysis-session/model/types';

describe('AGENT-VIEW-1: Per-Agent Views in Unified Reasoning Timeline (FLOW-1)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const sampleCompleteSteps: TraceStep[] = [
    {
      step_id: 'step-plan',
      seq: 1,
      t_ms: 100,
      actor: 'orchestrator',
      recipient: 'system',
      kind: 'plan',
      summary: 'Kế hoạch phân tích hồ sơ BID',
      detail: {
        question_type: 'company_profile',
        entities: ['BID'],
        metric_ids: ['bank.npl_g35', 'bank.llr_coverage'],
        periods: ['2026_Q1', '2026_Q2'],
        rationale_vi: 'Kế hoạch phân tích dạng hồ sơ doanh nghiệp cho BID dựa trên dữ liệu BCTC kiểm toán 2026.',
        tools: ['peer_position', 'trend'],
        agents: [
          { agent: 'company', decision: 'run' },
          { agent: 'verifier', decision: 'run' },
          { agent: 'critic', decision: 'run' }
        ]
      }
    },
    {
      step_id: 'step-assign-company',
      seq: 2,
      t_ms: 200,
      actor: 'orchestrator',
      recipient: 'company',
      kind: 'assign',
      summary: 'Giao việc: Phân tích số liệu và diễn biến của BID',
      detail: {
        task: 'Phân tích số liệu và diễn biến của BID',
        tools: ['trend']
      }
    },
    {
      step_id: 'step-assign-critic',
      seq: 3,
      t_ms: 300,
      actor: 'orchestrator',
      recipient: 'critic',
      kind: 'assign',
      summary: 'Giao việc: Rà soát tính chặt chẽ của nhận định',
      detail: {
        task: 'Rà soát tính chặt chẽ của nhận định',
        round: 1
      }
    },
    {
      step_id: 'step-tools-company',
      seq: 4,
      t_ms: 500,
      actor: 'company',
      recipient: 'orchestrator',
      kind: 'tool_result',
      summary: 'Trả 2 số liệu có nguồn',
      detail: {
        tool: 'trend',
        label: 'diễn biến chuỗi thời gian',
        duration_ms: 45,
        facts: [
          {
            fact_id: 'fact:value:BID:2026_Q2:bank.npl_g35',
            label: 'Tỷ lệ nợ xấu của BID trong quý 2/2026',
            display_value: '1,83%',
            source_note_no: 10
          },
          {
            fact_id: 'fact:value:BID:2026_Q2:bank.llr_coverage',
            label: 'Tỷ lệ bao phủ nợ xấu của BID trong quý 2/2026',
            display_value: '75,9%',
            source_note_no: 11
          }
        ]
      }
    },
    {
      step_id: 'step-draft-company',
      seq: 5,
      t_ms: 1000,
      actor: 'company',
      recipient: 'orchestrator',
      kind: 'draft',
      summary: 'Gửi 2 nhận định nháp',
      detail: {
        draft_text: 'Tỷ lệ nợ xấu BID ở mức 1,83% trong quý 2/2026.\n\nTỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.',
        sentences: [
          {
            sentence_id: 's-1',
            text: 'Tỷ lệ nợ xấu BID ở mức 1,83% trong quý 2/2026.'
          },
          {
            sentence_id: 's-2',
            text: 'Tỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.'
          }
        ]
      }
    },
    {
      step_id: 'step-verify',
      seq: 6,
      t_ms: 1300,
      actor: 'verifier',
      recipient: 'orchestrator',
      kind: 'verify',
      summary: 'Đã kiểm tra 2 số: 1 số khớp nguồn, loại 1 câu',
      detail: {
        numbers_checked: 2,
        numbers_matched: 1,
        sentences_checked: 2,
        verdicts: [
          {
            sentence: 'Tỷ lệ nợ xấu BID ở mức 1,83% trong quý 2/2026.',
            verdict: 'kept',
            source_note_no: 10,
            source_locator: 'BCTC Q2/2026 trang 15'
          },
          {
            sentence: 'Tỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.',
            verdict: 'dropped',
            drop_reason: 'unsupported_claim',
            explanation_vi: 'Số liệu 300% không tìm thấy trong BCTC'
          }
        ]
      }
    },
    {
      step_id: 'step-critique-issue',
      seq: 7,
      t_ms: 1600,
      actor: 'critic',
      recipient: 'company',
      kind: 'critique_issue',
      summary: 'Yêu cầu sửa 1 câu bị loại do sai số liệu',
      detail: {
        round: 1,
        issue_type: 'REMOVE_CLAIM',
        severity: 'MAJOR',
        target_sentence: 'Tỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.',
        required_action: 'Bỏ nhận định tăng đột biến 300% hoặc thay bằng số 75,9% từ fact đã trích xuất.'
      }
    },
    {
      step_id: 'step-revision-company',
      seq: 8,
      t_ms: 1900,
      actor: 'company',
      recipient: 'critic',
      kind: 'revision',
      summary: 'Cập nhật lại câu nhận định theo yêu cầu phản biện',
      detail: {
        round: 1,
        before: 'Tỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.',
        after: 'Tỷ lệ bao phủ nợ xấu thực tế đạt 75,9% trong quý 2/2026.',
        verified: true
      }
    },
    {
      step_id: 'step-accept-critic',
      seq: 9,
      t_ms: 2100,
      actor: 'critic',
      recipient: 'orchestrator',
      kind: 'accept',
      summary: 'Chấp nhận bản hiệu chỉnh: Lập luận chặt chẽ và số liệu đã kiểm định.',
      detail: { round: 1 }
    },
    {
      step_id: 'step-report-ready',
      seq: 10,
      t_ms: 2200,
      actor: 'orchestrator',
      recipient: null,
      kind: 'report_ready',
      summary: 'Báo cáo sẵn sàng',
      detail: {
        report_id: 'rep-agentview-test'
      }
    }
  ];

  describe('Requirement 1: Dòng suy luận thống nhất cho tất cả agent (FLOW-1)', () => {
    it('renders Orchestrator details: question type, plan, rationale, and collapsible detail', async () => {
      const user = userEvent.setup();
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Question type badge
      expect(screen.getAllByText('Hồ sơ doanh nghiệp').length).toBeGreaterThanOrEqual(1);

      // Plan entry exists in timeline
      const planBtn = screen.getByRole('button', { name: /Xem kế hoạch/i });
      expect(planBtn).toBeInTheDocument();

      // Open collapsible plan detail
      await user.click(planBtn);
      expect(screen.getByText('BID')).toBeInTheDocument();
      expect(screen.getByText('2026_Q1, 2026_Q2')).toBeInTheDocument();
      expect(screen.getByText('bank.npl_g35, bank.llr_coverage')).toBeInTheDocument();
    });

    it('renders Specialist details: tools run, sourced facts, draft sentences with verdicts and reasons', async () => {
      const user = userEvent.setup();
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Data extraction prose
      expect(screen.getByText(/Đã lấy 2 số liệu có nguồn từ phép phân tích diễn biến chuỗi thời gian/)).toBeInTheDocument();

      // Facts collapsible
      const factsBtn = screen.getByRole('button', { name: /Xem số liệu \(2\)/i });
      expect(factsBtn).toBeInTheDocument();
      await user.click(factsBtn);

      expect(screen.getByText(/Tỷ lệ nợ xấu của BID trong quý 2\/2026/)).toBeInTheDocument();
      expect(screen.getByText('1,83%')).toBeInTheDocument();
      expect(screen.getByText('75,9%')).toBeInTheDocument();

      // Sentence verdicts: kept and dropped with explanation
      expect(screen.getByText('Tỷ lệ nợ xấu BID ở mức 1,83% trong quý 2/2026.')).toBeInTheDocument();
      expect(screen.getByText(/khớp dữ kiện/)).toBeInTheDocument();
      expect(screen.getByText('Tỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.')).toBeInTheDocument();
      expect(screen.getByText(/bị loại: Số liệu 300% không tìm thấy trong BCTC/)).toBeInTheDocument();
    });

    it('renders Verifier details: verification step with numbers checked and matched', () => {
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      expect(screen.getByText(/Đối chiếu dữ liệu gốc: 1\/2 số liệu khớp/)).toBeInTheDocument();
    });

    it('renders Critic details: rounds, issues, and revisions', () => {
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Critique issue
      expect(screen.getByText(/Yêu cầu hiệu chỉnh \(vòng 1\)/)).toBeInTheDocument();

      // Revision
      expect(screen.getByText(/Đã sửa theo phản biện \(vòng 1\)/)).toBeInTheDocument();
      expect(screen.getByText(/Tỷ lệ bao phủ nợ xấu thực tế đạt 75,9% trong quý 2\/2026/)).toBeInTheDocument();
    });

    it('renders clean fallback states without raw model thoughts when agent has minimal data', () => {
      const emptySteps: TraceStep[] = [
        {
          step_id: 'step-1',
          seq: 1,
          t_ms: 100,
          actor: 'orchestrator',
          recipient: null,
          kind: 'plan',
          summary: 'Đang bắt đầu',
          detail: {}
        }
      ];

      render(
        <AgentStage
          steps={emptySteps}
          query="Tra cứu"
          live={false}
        />
      );

      // Does not throw, renders timeline cleanly
      expect(screen.getByRole('log')).toBeInTheDocument();
      expect(screen.getAllByText('Điều phối viên').length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Requirement 2: Compact horizontal agent chips (FLOW-1)', () => {
    it('generates agent chips with accurate countLabel based on real trace data', () => {
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Company chip shows (2 nhận định) derived from sentence count
      const companyChip = screen.getByRole('region', { name: 'Company' });
      expect(within(companyChip).getByText('(2 nhận định)')).toBeInTheDocument();

      // Verifier chip shows (2 số liệu)
      const verifierChip = screen.getByRole('region', { name: 'Kiểm tra số liệu' });
      expect(within(verifierChip).getByText('(2 số liệu)')).toBeInTheDocument();

      // Critic chip shows (1 góp ý)
      const criticChip = screen.getByRole('region', { name: 'Phản biện' });
      expect(within(criticChip).getByText('(1 góp ý)')).toBeInTheDocument();
    });
  });

  describe('Requirement 3: Đổi tên "tác tử" thành "agent" trong toàn bộ giao diện màn hình', () => {
    it('uses "agent" instead of "tác tử" in headers, descriptions, and labels', () => {
      const { container } = render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Verify "agent" is used in UI strings
      expect(screen.getByText('Agent:')).toBeInTheDocument();

      // Verify "tác tử" is NOT present anywhere in the rendered text
      expect(container.textContent).not.toContain('tác tử');
      expect(container.textContent).not.toContain('tác tử'.toLowerCase());
    });
  });

  describe('Requirement 4: Nút "Mở báo cáo" hiển thị nổi bật ở tiêu đề và không hiện khi từ chối', () => {
    it('renders prominent "Mở báo cáo" button in header when run is completed, and clicking calls onViewReport', async () => {
      const user = userEvent.setup();
      const onOpenReport = vi.fn();

      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
          reportId="rep-agentview-test"
          onOpenReport={onOpenReport}
        />
      );

      // Status indicator says "Đã hoàn tất"
      expect(screen.getByText('Đã hoàn tất')).toBeInTheDocument();

      // Report button exists in header and clicking it triggers onOpenReport
      const openButtons = screen.getAllByRole('button', { name: /Mở báo cáo/i });
      expect(openButtons.length).toBeGreaterThanOrEqual(1);

      // Click the first button (header button)
      await user.click(openButtons[0]);
      expect(onOpenReport).toHaveBeenCalledWith('rep-agentview-test');
    });

    it('does NOT render "Mở báo cáo" button when run is blocked or errored', () => {
      const onOpenReport = vi.fn();
      const blockedSteps: TraceStep[] = [
        {
          step_id: 'step-1',
          seq: 1,
          t_ms: 100,
          actor: 'system',
          recipient: null,
          kind: 'blocked',
          summary: 'Yêu cầu bị chặn',
          detail: {
            code: 'unsupported_metric',
            message: 'Chỉ tiêu không có trong dữ liệu'
          }
        }
      ];

      render(
        <AgentStage
          steps={blockedSteps}
          query="Chỉ tiêu lạ"
          live={false}
          reportId={null}
          onOpenReport={onOpenReport}
        />
      );

      // Status says "Từ chối"
      expect(screen.getByText('Từ chối')).toBeInTheDocument();

      // "Mở báo cáo" button MUST NOT be rendered
      expect(screen.queryByRole('button', { name: /Mở báo cáo/i })).not.toBeInTheDocument();
    });
  });

  describe('FIX1: Unused Agents and Blocked Handling (FLOW-1)', () => {
    it('completed run renders only participating agents in chip nav, excluding unused agents', () => {
      // In sampleCompleteSteps, macro was NOT in the plan and did NOT take part
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Participating agents have chips
      expect(screen.getByRole('region', { name: 'Điều phối viên' })).toBeInTheDocument();
      expect(screen.getByRole('region', { name: 'Company' })).toBeInTheDocument();
      expect(screen.getByRole('region', { name: 'Kiểm tra số liệu' })).toBeInTheDocument();
      expect(screen.getByRole('region', { name: 'Phản biện' })).toBeInTheDocument();

      // Macro was not participating, so it must not be rendered
      expect(screen.queryByRole('region', { name: 'Macro' })).not.toBeInTheDocument();
    });

    it('rejected/blocked run shows refusal reason in prose, not large red error box', () => {
      const refusalReason = 'Yêu cầu nằm ngoài phạm vi phân tích ngành ngân hàng.';
      const blockedSteps: TraceStep[] = [
        {
          step_id: 'step-block',
          seq: 1,
          t_ms: 100,
          actor: 'system',
          recipient: null,
          kind: 'blocked',
          summary: refusalReason,
          detail: {
            code: 'out_of_scope',
            message: refusalReason
          }
        }
      ];

      render(
        <AgentStage
          steps={blockedSteps}
          query="Thời tiết Hà Nội hôm nay thế nào?"
          live={false}
        />
      );

      // Header status shows "Từ chối"
      expect(screen.getByText('Từ chối')).toBeInTheDocument();

      // Timeline entry shows refusal reason
      expect(screen.getByText(refusalReason)).toBeInTheDocument();
    });
  });

  describe('FIX2: Filtering Timeline by Agent Chip', () => {
    it('filters entries when an agent chip is clicked and resets when unclicked', async () => {
      const user = userEvent.setup();
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // All agent entries are initially visible
      expect(screen.getByText(/Đã lấy 2 số liệu có nguồn từ phép phân tích/)).toBeInTheDocument();
      expect(screen.getByText(/Đối chiếu dữ liệu gốc: 1\/2 số liệu khớp/)).toBeInTheDocument();

      // Click on Verifier chip
      const verifierChip = screen.getByRole('region', { name: 'Kiểm tra số liệu' });
      const verifierBtn = verifierChip.querySelector('button')!;
      await user.click(verifierBtn);

      expect(verifierBtn).toHaveAttribute('aria-pressed', 'true');

      // Verifier entry is visible, Company entry is hidden
      expect(screen.getByText(/Đối chiếu dữ liệu gốc: 1\/2 số liệu khớp/)).toBeInTheDocument();
      expect(screen.queryByText(/Đã lấy 2 số liệu có nguồn từ phép phân tích/)).not.toBeInTheDocument();

      // Click "Xem tất cả" to reset filter
      const resetBtn = screen.getByRole('button', { name: 'Xem tất cả' });
      await user.click(resetBtn);

      expect(screen.getByText(/Đã lấy 2 số liệu có nguồn từ phép phân tích/)).toBeInTheDocument();
    });
  });
});
