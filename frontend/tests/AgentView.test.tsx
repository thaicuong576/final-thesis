import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AgentStage } from '../src/features/analysis-session/components/AgentStage';
import type { TraceStep } from '../src/features/analysis-session/model/types';

describe('AGENT-VIEW-1: Per-Agent Views, Card Summaries, and Report CTA', () => {
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
            sentence_id: 'sent-1',
            text: 'Tỷ lệ nợ xấu BID ở mức 1,83% trong quý 2/2026.',
            fact_ids: ['fact:value:BID:2026_Q2:bank.npl_g35']
          },
          {
            sentence_id: 'sent-2',
            text: 'Tỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.',
            fact_ids: []
          }
        ]
      }
    },
    {
      step_id: 'step-verify',
      seq: 6,
      t_ms: 1200,
      actor: 'verifier',
      recipient: 'orchestrator',
      kind: 'verify',
      summary: '1/2 số khớp dữ liệu gốc; 1 câu bị loại',
      detail: {
        sentences_checked: 2,
        numbers_checked: 2,
        numbers_matched: 1,
        verdicts: [
          {
            sentence: 'Tỷ lệ nợ xấu BID ở mức 1,83% trong quý 2/2026.',
            verdict: 'kept',
            explanationVi: 'Đã đối chiếu dữ liệu gốc',
            factIds: ['fact:value:BID:2026_Q2:bank.npl_g35'],
            role: 'company'
          },
          {
            sentence: 'Tỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.',
            verdict: 'dropped',
            dropReason: 'unsupported_claim',
            explanationVi: 'Số liệu 300% không tìm thấy trong BCTC',
            factIds: [],
            role: 'company'
          }
        ]
      }
    },
    {
      step_id: 'step-critique',
      seq: 7,
      t_ms: 1500,
      actor: 'critic',
      recipient: 'company',
      kind: 'critique_issue',
      summary: 'Yêu cầu sửa: Bỏ câu nhận định số liệu không có căn cứ',
      detail: {
        round: 1,
        issue_type: 'unsupported_claim',
        severity: 'MAJOR',
        target_sentence: 'Tỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.',
        required_action: 'REMOVE_CLAIM',
        description: 'Bỏ nhận định tăng đột biến 300% do vi phạm kiểm định số liệu.'
      }
    },
    {
      step_id: 'step-revision',
      seq: 8,
      t_ms: 1800,
      actor: 'company',
      recipient: 'critic',
      kind: 'revision',
      summary: 'Hiệu chỉnh: Loại bỏ câu không có căn cứ',
      detail: {
        round: 1,
        before: 'Tỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.',
        after: 'Tỷ lệ bao phủ nợ xấu thực tế đạt 75,9% trong quý 2/2026.'
      }
    },
    {
      step_id: 'step-accept',
      seq: 9,
      t_ms: 2000,
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

  describe('Requirement 1: Khối chi tiết theo agent (LiveWorkPane)', () => {
    it('renders Orchestrator details: question type, plan, rationale, assignments, and summary', async () => {
      const user = userEvent.setup();
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Select Orchestrator card
      const orchCard = screen.getByRole('region', { name: 'Điều phối viên' });
      await user.click(orchCard);

      // Verify pane region
      const pane = screen.getByRole('region', { name: 'Chi tiết hoạt động của Điều phối viên' });
      expect(pane).toBeInTheDocument();

      // Dạng câu hỏi & Kế hoạch
      expect(within(pane).getAllByText('Hồ sơ doanh nghiệp').length).toBeGreaterThanOrEqual(1);
      expect(within(pane).getByText('BID')).toBeInTheDocument();
      expect(within(pane).getByText('2026_Q1, 2026_Q2')).toBeInTheDocument();
      expect(within(pane).getByText('bank.npl_g35')).toBeInTheDocument();
      expect(within(pane).getByText('bank.llr_coverage')).toBeInTheDocument();

      // Lý do chọn kế hoạch (Rationale)
      expect(
        within(pane).getByText(/Kế hoạch phân tích dạng hồ sơ doanh nghiệp cho BID dựa trên dữ liệu BCTC/i)
      ).toBeInTheDocument();

      // Nhiệm vụ & công cụ đã giao
      expect(within(pane).getByText('Nhiệm vụ & Công cụ đã giao')).toBeInTheDocument();
      expect(within(pane).getByText('Phân tích số liệu và diễn biến của BID')).toBeInTheDocument();
      expect(within(pane).getByText('Rà soát tính chặt chẽ của nhận định')).toBeInTheDocument();
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

      // Select Company specialist card
      const companyCard = screen.getByRole('region', { name: 'Company' });
      await user.click(companyCard);

      const pane = screen.getByRole('region', { name: 'Chi tiết hoạt động của Chuyên viên doanh nghiệp' });
      expect(pane).toBeInTheDocument();

      // Tool calls & facts
      expect(within(pane).getByText('Truy vấn dữ liệu (1)')).toBeInTheDocument();
      expect(within(pane).getByText('trend')).toBeInTheDocument();
      expect(within(pane).getByText('45ms')).toBeInTheDocument();
      expect(within(pane).getByText(/Tỷ lệ nợ xấu của BID trong quý 2\/2026/)).toBeInTheDocument();
      expect(within(pane).getByText('1,83%')).toBeInTheDocument();
      expect(within(pane).getByText('Ghi chú 10')).toBeInTheDocument();

      // Sentence verdicts: kept and dropped with explanation
      expect(within(pane).getByText('Tỷ lệ nợ xấu BID ở mức 1,83% trong quý 2/2026.')).toBeInTheDocument();
      expect(within(pane).getByText('Tỷ lệ bao phủ nợ xấu tăng đột biến lên 300%.')).toBeInTheDocument();
      expect(within(pane).getByText(/Lý do: Số liệu 300% không tìm thấy trong BCTC/)).toBeInTheDocument();
    });

    it('renders Verifier details: checked stats, dropped sentences with reasons, and kept sentences', async () => {
      const user = userEvent.setup();
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Select Verifier card
      const verifierCard = screen.getByRole('region', { name: 'Kiểm tra số liệu' });
      await user.click(verifierCard);

      const pane = screen.getByRole('region', { name: 'Chi tiết hoạt động của Kiểm tra số liệu' });
      expect(pane).toBeInTheDocument();

      // Verification stats
      expect(within(pane).getByText('Tổng hợp kiểm định số liệu')).toBeInTheDocument();
      expect(within(pane).getByText('1/2')).toBeInTheDocument(); // 1/2 số khớp

      // Dropped sentences section with reason
      expect(within(pane).getByText('Các câu bị loại (1)')).toBeInTheDocument();
      expect(within(pane).getByText(/Lý do loại: Số liệu 300% không tìm thấy trong BCTC/)).toBeInTheDocument();
    });

    it('renders Critic details: rounds, issues with severity and required action, and revisions', async () => {
      const user = userEvent.setup();
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Select Critic card
      const criticCard = screen.getByRole('region', { name: 'Phản biện' });
      await user.click(criticCard);

      const pane = screen.getByRole('region', { name: 'Chi tiết hoạt động của Phản biện' });
      expect(pane).toBeInTheDocument();

      // Review progress & acceptance
      expect(within(pane).getByText(/Chấp nhận bản hiệu chỉnh: Lập luận chặt chẽ/)).toBeInTheDocument();

      // Issues section
      expect(within(pane).getByText('Vấn đề & Yêu cầu sửa (1)')).toBeInTheDocument();
      expect(within(pane).getByText('REMOVE_CLAIM')).toBeInTheDocument();
      expect(within(pane).getByText('MAJOR')).toBeInTheDocument();
      expect(within(pane).getByText(/Bỏ nhận định tăng đột biến 300%/)).toBeInTheDocument();

      // Revisions section
      expect(within(pane).getByText('Kết quả sau sửa (1)')).toBeInTheDocument();
      expect(within(pane).getByText('Tỷ lệ bao phủ nợ xấu thực tế đạt 75,9% trong quý 2/2026.')).toBeInTheDocument();
      expect(within(pane).getByText('Đã kiểm định lại')).toBeInTheDocument();
    });

    it('renders clean fallback states without raw model thoughts when agent has no data', async () => {
      const user = userEvent.setup();
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

      const orchCard = screen.getByRole('region', { name: 'Điều phối viên' });
      await user.click(orchCard);

      // Does not throw, renders honest fallbacks
      expect(screen.getByText('Chưa có kế hoạch phân tích.')).toBeInTheDocument();
      expect(screen.getByText('Chưa có thông tin lý do chọn kế hoạch.')).toBeInTheDocument();
      expect(screen.getByText('Chưa phân công công cụ.')).toBeInTheDocument();
    });
  });

  describe('Requirement 2: Thẻ agent ở hàng trên có dòng tóm tắt ngắn do dữ liệu thật tạo ra', () => {
    it('generates accurate summaryLine for each card based on real trace data', () => {
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Company card: 2 sentences drafted, 1 dropped -> "Viết 2 nhận định, 1 bị loại"
      expect(screen.getByText('Viết 2 nhận định, 1 bị loại')).toBeInTheDocument();

      // Orchestrator card: "Kế hoạch Hồ sơ doanh nghiệp: BID"
      expect(screen.getByText('Kế hoạch Hồ sơ doanh nghiệp: BID')).toBeInTheDocument();

      // Verifier card: "Đã kiểm 2 số, 1 khớp (1 câu bị loại)"
      expect(screen.getByText('Đã kiểm 2 số, 1 khớp (1 câu bị loại)')).toBeInTheDocument();

      // Critic card: "1 vòng, 1 yêu cầu sửa"
      expect(screen.getByText('1 vòng, 1 yêu cầu sửa')).toBeInTheDocument();
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
      expect(screen.getByText('Luồng xử lý giữa các agent')).toBeInTheDocument();
      expect(screen.getByText('Nhấn vào agent để xem chi tiết')).toBeInTheDocument();

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

      // Status says "Yêu cầu bị từ chối"
      expect(screen.getByText('Yêu cầu bị từ chối')).toBeInTheDocument();

      // "Mở báo cáo" button MUST NOT be rendered
      expect(screen.queryByRole('button', { name: /Mở báo cáo/i })).not.toBeInTheDocument();
    });
  });

  describe('FIX1: Single Source of Truth, Unused Agents, and Blocked Summary', () => {
    it('completed run marks participating agents as "Xong" and non-participating as "Không tham gia", NOT "Chờ"', () => {
      // In sampleCompleteSteps, macro was NOT in the plan and did NOT take part
      render(
        <AgentStage
          steps={sampleCompleteSteps}
          query="Phân tích chất lượng tài sản của BID"
          live={false}
        />
      );

      // Orchestrator card shows "Xong"
      const orchCard = screen.getByRole('region', { name: 'Điều phối viên' });
      expect(within(orchCard).getByText('Xong')).toBeInTheDocument();
      expect(within(orchCard).getByText('Kế hoạch Hồ sơ doanh nghiệp: BID')).toBeInTheDocument();

      // Company card shows "Xong"
      const companyCard = screen.getByRole('region', { name: 'Company' });
      expect(within(companyCard).getByText('Xong')).toBeInTheDocument();
      expect(within(companyCard).getByText('Viết 2 nhận định, 1 bị loại')).toBeInTheDocument();

      // Verifier card shows "Xong"
      const verifierCard = screen.getByRole('region', { name: 'Kiểm tra số liệu' });
      expect(within(verifierCard).getByText('Xong')).toBeInTheDocument();
      expect(within(verifierCard).getByText('Đã kiểm 2 số, 1 khớp (1 câu bị loại)')).toBeInTheDocument();

      // Critic card shows "Xong"
      const criticCard = screen.getByRole('region', { name: 'Phản biện' });
      expect(within(criticCard).getByText('Xong')).toBeInTheDocument();
      expect(within(criticCard).getByText('1 vòng, 1 yêu cầu sửa')).toBeInTheDocument();

      // None of the cards say "Chờ" when completed
      expect(screen.queryByText('Chờ')).not.toBeInTheDocument();
    });

    it('rejected/blocked run shows refusal reason and "Từ chối" across cards, NEVER "Chờ"', () => {
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

      // Card must show "Từ chối", NOT "Chờ"
      const orchCard = screen.getByRole('region', { name: 'Điều phối viên' });
      expect(within(orchCard).getByText('Từ chối')).toBeInTheDocument();
      expect(within(orchCard).getAllByText(refusalReason).length).toBeGreaterThanOrEqual(1);

      // None of the cards say "Chờ"
      expect(screen.queryByText('Chờ')).not.toBeInTheDocument();

      // Detail pane shows refusal reason alert
      const pane = screen.getByRole('region', { name: 'Chi tiết hoạt động của Điều phối viên' });
      expect(within(pane).getByText(/Yêu cầu bị từ chối \/ Ngoài phạm vi phân tích/i)).toBeInTheDocument();
      expect(within(pane).getByText(refusalReason)).toBeInTheDocument();
    });
  });

  describe('FIX2: Live SSE Streaming, Viewport Stability, and Auto-Follow', () => {
    it('appends live streaming draft text, sentence verdicts, and tool facts as events arrive', () => {
      const partialLiveState = {
        activeWriterRole: 'company',
        draftsByRole: {
          company: 'ACB có tỷ lệ nợ xấu 1,03% trong quý 2/2026. Tỷ lệ bao phủ nợ xấu đạt 105,3%.'
        },
        verdictsByRole: {
          company: [
            {
              sentence: 'ACB có tỷ lệ nợ xấu 1,03% trong quý 2/2026.',
              verdict: 'kept' as const,
              explanationVi: 'Số liệu khớp với BCTC Q2/2026'
            },
            {
              sentence: 'Tỷ lệ bao phủ nợ xấu đạt 105,3%.',
              verdict: 'kept' as const,
              explanationVi: 'Số liệu khớp với BCTC Q2/2026'
            }
          ]
        },
        toolCallsByRole: {
          company: [
            {
              tool: 'head_to_head',
              status: 'completed' as const,
              resultCount: 2,
              durationMs: 120,
              role: 'company',
              facts: [
                {
                  factId: 'f-1',
                  label: 'Tỷ lệ nợ xấu ACB Q2/2026',
                  displayValue: '1,03%',
                  sourceNoteNo: 15
                }
              ]
            }
          ]
        }
      };

      const steps: TraceStep[] = [
        {
          step_id: 's-1',
          seq: 1,
          t_ms: 100,
          actor: 'orchestrator',
          recipient: 'company',
          kind: 'assign',
          summary: 'Giao việc cho Company',
          detail: {}
        }
      ];

      render(
        <AgentStage
          steps={steps}
          query="So sánh ACB và TCB"
          live={true}
          liveWorkState={partialLiveState}
        />
      );

      // Auto-follows company since activeWriterRole is 'company'
      const pane = screen.getByRole('region', { name: 'Chi tiết hoạt động của Chuyên viên doanh nghiệp' });
      expect(pane).toBeInTheDocument();

      // Check tool call fact rendered immediately
      expect(within(pane).getByText('1,03%')).toBeInTheDocument();
      expect(within(pane).getByText('Ghi chú 15')).toBeInTheDocument();

      // Check verdicts rendered immediately
      expect(within(pane).getByText('ACB có tỷ lệ nợ xấu 1,03% trong quý 2/2026.')).toBeInTheDocument();
      expect(within(pane).getByText('Tỷ lệ bao phủ nợ xấu đạt 105,3%.')).toBeInTheDocument();
      expect(within(pane).getByText('2 đạt · 0 loại')).toBeInTheDocument();
    });

    it('auto-follows active writer, but if user clicks another agent it pins user choice and shows resume hint', async () => {
      const user = userEvent.setup();
      const liveState = {
        activeWriterRole: 'company',
        draftsByRole: { company: 'Đang viết nhận định...' }
      };

      const steps: TraceStep[] = [
        {
          step_id: 's-1',
          seq: 1,
          t_ms: 100,
          actor: 'orchestrator',
          recipient: 'company',
          kind: 'assign',
          summary: 'Giao việc cho Company',
          detail: {}
        }
      ];

      render(
        <AgentStage
          steps={steps}
          query="So sánh ACB và TCB"
          live={true}
          liveWorkState={liveState}
        />
      );

      // Initially auto-follows 'company'
      expect(
        screen.getByRole('region', { name: 'Chi tiết hoạt động của Chuyên viên doanh nghiệp' })
      ).toBeInTheDocument();

      // User explicitly clicks 'Điều phối viên' card
      const orchCard = screen.getByRole('region', { name: 'Điều phối viên' });
      await user.click(orchCard);

      // Detail panel switched to user's choice (Orchestrator)
      expect(
        screen.getByRole('region', { name: 'Chi tiết hoạt động của Điều phối viên' })
      ).toBeInTheDocument();

      // Shows hint: "Đang chạy ở Chuyên viên doanh nghiệp · Nhấn để theo dõi"
      const resumeBtn = screen.getByRole('button', { name: /Đang chạy ở Chuyên viên doanh nghiệp/i });
      expect(resumeBtn).toBeInTheDocument();
      expect(within(resumeBtn).getByText('Nhấn để theo dõi')).toBeInTheDocument();

      // User clicks resume hint
      await user.click(resumeBtn);

      // View resumes auto-follow back to 'company'
      expect(
        screen.getByRole('region', { name: 'Chi tiết hoạt động của Chuyên viên doanh nghiệp' })
      ).toBeInTheDocument();
    });
  });
});

