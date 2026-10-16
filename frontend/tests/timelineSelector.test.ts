import { describe, it, expect } from 'vitest';
import { deriveTimeline, formatClock } from '../src/features/analysis-session/model/timeline';
import type { TraceStep } from '../src/features/analysis-session/model/types';

describe('formatClock', () => {
  it('formats ms into mm:ss correctly', () => {
    expect(formatClock(0)).toBe('00:00');
    expect(formatClock(4730)).toBe('00:04');
    expect(formatClock(25889)).toBe('00:25');
    expect(formatClock(87149)).toBe('01:27');
  });
});

describe('deriveTimeline selector', () => {
  it('transforms planned steps into ordered timeline entries with first-person Vietnamese narrative and NO placeholders', () => {
    const steps: TraceStep[] = [
      {
        step_id: 't-1',
        seq: 1,
        t_ms: 4373,
        actor: 'orchestrator',
        recipient: 'system',
        kind: 'plan',
        summary: 'Dạng câu hỏi: Trực diện.',
        detail: {
          question_type: 'head_to_head',
          rationale: 'Dùng công cụ head_to_head để so sánh trực tiếp ACB và TCB.',
          entities: ['ACB', 'TCB'],
          periods: ['2026_Q2'],
          metric_ids: ['bank.roe']
        }
      },
      {
        step_id: 't-2',
        seq: 2,
        t_ms: 9997,
        actor: 'company',
        recipient: 'orchestrator',
        kind: 'tool_result',
        summary: 'Trả 22 số liệu có nguồn',
        detail: {
          tool: 'head_to_head',
          label: 'so sánh trực diện',
          result_count: 22,
          duration_ms: 1188,
          facts: [
            {
              fact_id: 'f1',
              label: 'ROE của ACB',
              display_value: '16,2%',
              source_note_no: null
            }
          ]
        }
      },
      {
        step_id: 't-3',
        seq: 3,
        t_ms: 25532,
        actor: 'company',
        recipient: 'orchestrator',
        kind: 'draft',
        summary: 'Gửi 4 nhận định nháp',
        detail: {
          draft_text: 'Quý 2/2026, ACB có tỷ suất sinh lời trên vốn chủ sở hữu 16,2%.',
          sentences: [
            {
              sentence_id: 's1',
              text: 'Quý 2/2026, ACB có tỷ suất sinh lời trên vốn chủ sở hữu 16,2%.'
            }
          ]
        }
      },
      {
        step_id: 't-4',
        seq: 4,
        t_ms: 25593,
        actor: 'verifier',
        recipient: 'orchestrator',
        kind: 'verify',
        summary: '1/1 số khớp dữ liệu gốc',
        detail: {
          sentences_checked: 1,
          numbers_checked: 1,
          numbers_matched: 1,
          verdicts: [
            {
              sentence: 'Quý 2/2026, ACB có tỷ suất sinh lời trên vốn chủ sở hữu 16,2%.',
              verdict: 'kept'
            }
          ],
          dropped: []
        }
      },
      {
        step_id: 't-5',
        seq: 5,
        t_ms: 56591,
        actor: 'critic',
        recipient: 'orchestrator',
        kind: 'critique_issue',
        summary: 'Yêu cầu sửa: Cần bổ sung nhận định về rủi ro.',
        detail: {
          round: 1,
          description: 'Cần bổ sung nhận định về rủi ro.',
          severity: 'MAJOR'
        }
      },
      {
        step_id: 't-6',
        seq: 6,
        t_ms: 62682,
        actor: 'orchestrator',
        recipient: 'verifier',
        kind: 'revision',
        summary: 'Đã sửa theo phản biện',
        detail: {
          round: 1,
          after: 'Đã bổ sung rủi ro nợ xấu quý 2/2026.'
        }
      },
      {
        step_id: 't-7',
        seq: 7,
        t_ms: 86791,
        actor: 'orchestrator',
        recipient: 'system',
        kind: 'report_ready',
        summary: 'Báo cáo sẵn sàng',
        detail: {
          report_id: 'rep-123'
        }
      }
    ];

    const result = deriveTimeline(steps, undefined, { isStreaming: false, reportId: 'rep-123' });

    expect(result.entries.length).toBe(7);
    expect(result.isComplete).toBe(true);
    expect(result.reportId).toBe('rep-123');

    // Step 1: plan
    expect(result.entries[0].kind).toBe('plan');
    expect(result.entries[0].formattedTime).toBe('00:04');
    expect(result.entries[0].agentName).toBe('Điều phối viên');
    expect(result.entries[0].prose).toContain('so sánh trực diện');
    expect(result.entries[0].planDetail?.entities).toEqual(['ACB', 'TCB']);

    // Step 2: data
    expect(result.entries[1].kind).toBe('data');
    expect(result.entries[1].agentName).toBe('Chuyên viên doanh nghiệp');
    expect(result.entries[1].prose).toContain('22 số liệu có nguồn');
    expect(result.entries[1].facts?.length).toBe(1);

    // Step 3: draft
    expect(result.entries[2].kind).toBe('draft');
    expect(result.entries[2].draftDetail?.text).toContain('Quý 2/2026, ACB có tỷ suất');

    // Step 4: verify
    expect(result.entries[3].kind).toBe('verification');
    expect(result.entries[3].agentName).toBe('Kiểm tra số liệu');
    expect(result.entries[3].prose).toContain('1/1 số liệu khớp');

    // Step 5: critique
    expect(result.entries[4].kind).toBe('critique');
    expect(result.entries[4].agentName).toBe('Phản biện');
    expect(result.entries[4].prose).toContain('Yêu cầu hiệu chỉnh (vòng 1)');

    // Step 6: revision
    expect(result.entries[5].kind).toBe('revision');
    expect(result.entries[5].prose).toContain('Đã sửa theo phản biện (vòng 1)');

    // Step 7: complete
    expect(result.entries[6].kind).toBe('complete');
    expect(result.entries[6].reportId).toBe('rep-123');

    // Participating agents:
    // Only orchestrator, company, verifier, critic participated (macro and sector did not)
    const agentIds = result.participatingAgents.map((a) => a.id);
    expect(agentIds).toContain('orchestrator');
    expect(agentIds).toContain('company');
    expect(agentIds).toContain('verifier');
    expect(agentIds).toContain('critic');
    expect(agentIds).not.toContain('macro');
    expect(agentIds).not.toContain('sector');
  });

  it('renders a single live tail item when streaming is active', () => {
    const steps: TraceStep[] = [
      {
        step_id: 't-1',
        seq: 1,
        t_ms: 4000,
        actor: 'orchestrator',
        recipient: 'system',
        kind: 'plan',
        summary: 'Lập kế hoạch',
        detail: { question_type: 'ranking' }
      }
    ];

    const result = deriveTimeline(
      steps,
      {
        activeWriterRole: 'company',
        draftsByRole: { company: 'Đang viết nhận định về' }
      },
      { isStreaming: true, elapsedMs: 12000 }
    );

    expect(result.liveTail).not.toBeNull();
    expect(result.liveTail?.formattedTime).toBe('00:12');
    expect(result.liveTail?.agentName).toBe('Chuyên viên doanh nghiệp');
    expect(result.liveTail?.activity).toBe('Đang viết nhận định...');
  });

  it('handles blocked status with prose refusal and suggested inquiries', () => {
    const steps: TraceStep[] = [
      {
        step_id: 'b-1',
        seq: 1,
        t_ms: 1200,
        actor: 'system',
        recipient: null,
        kind: 'blocked',
        summary: 'Yêu cầu nằm ngoài phạm vi phân tích',
        detail: {
          message: 'Hệ thống chỉ hỗ trợ phân tích dữ liệu ngành ngân hàng.',
          suggestions: ['Phân tích ROE của VCB', 'So sánh nợ xấu ACB và TCB']
        }
      }
    ];

    const result = deriveTimeline(steps, undefined, { isStreaming: false });

    expect(result.isBlocked).toBe(true);
    expect(result.entries.length).toBe(1);
    expect(result.entries[0].kind).toBe('blocked');
    expect(result.entries[0].prose).toBe('Hệ thống chỉ hỗ trợ phân tích dữ liệu ngành ngân hàng.');
    expect(result.entries[0].blockedDetail?.suggestions?.length).toBe(2);
  });

  describe('FIX1 Review Verification Tests', () => {
    it('maps all role IDs to Vietnamese names and never prints raw role IDs', () => {
      const steps: TraceStep[] = [
        {
          step_id: 't-raw-1',
          seq: 1,
          t_ms: 100,
          actor: 'specialist' as unknown as 'company',
          recipient: null,
          kind: 'tool_result',
          summary: 'Trả 10 số liệu',
          detail: { tool: 'head_to_head', label: 'so sánh trực diện', result_count: 10 }
        },
        {
          step_id: 't-raw-2',
          seq: 2,
          t_ms: 200,
          actor: 'orchestrator',
          recipient: null,
          kind: 'compose',
          summary: 'Dựng báo cáo',
          detail: { draft_text: 'ACB có tỷ lệ nợ xấu thấp hơn TCB.' }
        }
      ];

      const result = deriveTimeline(steps, undefined, { isStreaming: false });
      for (const entry of result.entries) {
        expect(entry.agentName).not.toBe('specialist');
        expect(entry.agentName).not.toBe('company');
        expect(entry.agentName).not.toBe('orchestrator');
        expect(entry.agentName).toMatch(/^(Điều phối viên|Chuyên viên doanh nghiệp|Chuyên viên ngành|Chuyên viên vĩ mô|Kiểm tra số liệu|Phản biện|Hệ thống)$/);
      }
    });

    it('deduplicates logical tool calls and steps between TRACE_STEP and liveWorkState', () => {
      const steps: TraceStep[] = [
        {
          step_id: 'step-data-1',
          seq: 1,
          t_ms: 1000,
          actor: 'company',
          recipient: null,
          kind: 'tool_result',
          summary: 'Trả 22 số liệu',
          detail: {
            tool: 'head_to_head',
            label: 'so sánh trực diện',
            result_count: 22,
            duration_ms: 1200
          }
        }
      ];

      const liveWorkState = {
        toolCallsByRole: {
          company: [
            {
              tool: 'head_to_head',
              status: 'completed' as const,
              resultCount: 22,
              durationMs: 1200,
              role: 'company'
            }
          ]
        }
      };

      const result = deriveTimeline(steps, liveWorkState, { isStreaming: false });
      const dataEntries = result.entries.filter((e) => e.kind === 'data');
      expect(dataEntries.length).toBe(1);
    });

    it('enforces strict terminal ordering: nothing may appear after final "Báo cáo sẵn sàng"', () => {
      const steps: TraceStep[] = [
        {
          step_id: 't-plan',
          seq: 1,
          t_ms: 1000,
          actor: 'orchestrator',
          recipient: null,
          kind: 'plan',
          summary: 'Lập kế hoạch',
          detail: {}
        },
        {
          step_id: 't-ready-1',
          seq: 2,
          t_ms: 5000,
          actor: 'orchestrator',
          recipient: null,
          kind: 'report_ready',
          summary: 'Báo cáo sẵn sàng',
          detail: { report_id: 'rep-final-order' }
        },
        {
          step_id: 't-ready-dup',
          seq: 3,
          t_ms: 5100,
          actor: 'orchestrator',
          recipient: null,
          kind: 'report_ready',
          summary: 'Báo cáo sẵn sàng',
          detail: { report_id: 'rep-final-order' }
        }
      ];

      // Live work state lingering with late tool call
      const liveWorkState = {
        toolCallsByRole: {
          specialist: [
            {
              tool: 'head_to_head',
              status: 'completed' as const,
              resultCount: 22,
              role: 'specialist'
            }
          ]
        }
      };

      const result = deriveTimeline(steps, liveWorkState, { isStreaming: false });
      const readyEntries = result.entries.filter((e) => e.kind === 'complete');
      expect(readyEntries.length).toBe(1);
      const lastEntry = result.entries[result.entries.length - 1];
      expect(lastEntry.kind).toBe('complete');
      expect(lastEntry.prose).toMatch(/Báo cáo/);
    });

    it('scrubs snake_case identifiers, fact_ids, and raw internal markers from prose and drafts', () => {
      const steps: TraceStep[] = [
        {
          step_id: 't-draft',
          seq: 1,
          t_ms: 1000,
          actor: 'orchestrator',
          recipient: null,
          kind: 'compose',
          summary: 'Dựng bản nháp',
          detail: {
            draft_text: 'fact_ids: fact:value:ACB:2024_Q4:bank.roe ACB dẫn đầu về ROE. fact_ids: fact:value:TCB:2024_Q4:bank.roe TCB có nợ xấu thấp trong sector:bank.'
          }
        },
        {
          step_id: 't-critic',
          seq: 2,
          t_ms: 2000,
          actor: 'critic',
          recipient: null,
          kind: 'critique_issue',
          summary: 'Khối đầu tiên được khai báo là headline nhưng không có nội dung; report_level_synthesis thiếu so sánh',
          detail: {
            round: 1,
            issue_type: 'report_level_synthesis',
            severity: 'critical',
            description: 'Khối đầu tiên được khai báo là headline nhưng không có nội dung; report_level_synthesis thiếu so sánh'
          }
        }
      ];

      const result = deriveTimeline(steps, undefined, { isStreaming: false });

      // Join all text in timeline
      const fullProse = result.entries
        .map((e) => `${e.prose} ${e.draftDetail?.text || ''}`)
        .join(' ');

      // Must not leak fact_ids or internal names
      expect(fullProse).not.toContain('fact_ids');
      expect(fullProse).not.toContain('sector:bank');
      expect(fullProse).not.toContain('report_level_synthesis');

      // Assert no snake_case identifiers exist in prose
      const snakeMatches = fullProse.match(/\b[a-z]+_[a-z_]+\b/g) || [];
      expect(snakeMatches).toEqual([]);
    });

    it('shows chips ONLY for participating agents that actually have events', () => {
      const steps: TraceStep[] = [
        {
          step_id: 't-plan',
          seq: 1,
          t_ms: 100,
          actor: 'orchestrator',
          recipient: null,
          kind: 'plan',
          summary: 'Lập kế hoạch',
          detail: {
            question_type: 'head_to_head',
            // sector was planned but did not execute!
            agents: [
              { agent: 'company', decision: 'run' },
              { agent: 'sector', decision: 'run' },
              { agent: 'verifier', decision: 'run' }
            ]
          }
        },
        {
          step_id: 't-tool',
          seq: 2,
          t_ms: 500,
          actor: 'company',
          recipient: null,
          kind: 'tool_result',
          summary: 'Trả 22 số liệu',
          detail: { tool: 'head_to_head', label: 'so sánh trực diện', result_count: 22 }
        },
        {
          step_id: 't-draft',
          seq: 3,
          t_ms: 1000,
          actor: 'company',
          recipient: null,
          kind: 'draft',
          summary: 'Nháp nhận định',
          detail: {
            draft_text: 'Câu 1. Câu 2. Câu 3. Câu 4.'
          }
        }
      ];

      const result = deriveTimeline(steps, undefined, { isStreaming: false });
      const chipIds = result.participatingAgents.map((c) => c.id);

      // Orchestrator and Company participated
      expect(chipIds).toContain('orchestrator');
      expect(chipIds).toContain('company');

      // Sector and Verifier did NOT have any event and must be omitted
      expect(chipIds).not.toContain('sector');
      expect(chipIds).not.toContain('verifier');
      expect(chipIds).not.toContain('macro');

      // Count label on company derives from 4 sentences
      const companyChip = result.participatingAgents.find((c) => c.id === 'company');
      expect(companyChip?.countLabel).toBe('4 nhận định');
    });

    it('humanizes period label in orchestrator plan entry without raw period id', () => {
      const steps: TraceStep[] = [
        {
          step_id: 't-plan-period',
          seq: 1,
          t_ms: 1000,
          actor: 'orchestrator',
          recipient: 'system',
          kind: 'plan',
          summary: 'Kế hoạch phân tích',
          detail: {
            question_type: 'head_to_head',
            entities: ['VCB', 'TCB'],
            periods: ['2024_Q4'],
            metrics: ['bank.nim']
          }
        }
      ];

      const result = deriveTimeline(steps, undefined, { isStreaming: false });
      const planEntry = result.entries[0];

      expect(planEntry.prose).toMatch(/quý 4\/2024/);
      expect(planEntry.prose).not.toMatch(/\d{4}_Q\d/);
    });
  });
});
