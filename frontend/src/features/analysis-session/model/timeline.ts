import type { TraceStep } from './types';
import {
  STAGE_AGENTS,
  QUESTION_TYPES,
  readerText,
  type StageAgentId,
  type StageAgentState,
  type SourcedFact,
  type SentenceVerdictDetail,
  type ToolCallDetail,
  type ReviewIssueDetail,
  type SentenceRevisionDetail,
  type PlanSummaryDetail,
  type LiveWorkStateInput
} from './agentStage';

export function formatClock(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export type TimelineEntryKind =
  | 'plan'
  | 'data'
  | 'draft'
  | 'verification'
  | 'critique'
  | 'revision'
  | 'accept'
  | 'complete'
  | 'blocked';

export interface TimelineEntry {
  id: string;
  tMs: number;
  formattedTime: string;
  agentId: StageAgentId | 'system';
  agentName: string;
  kind: TimelineEntryKind;
  prose: string;
  planDetail?: PlanSummaryDetail;
  facts?: SourcedFact[];
  toolDetail?: {
    tool: string;
    label?: string;
    durationMs?: number;
    resultCount?: number;
  };
  draftDetail?: {
    text: string;
    isStreaming: boolean;
    verdicts?: SentenceVerdictDetail[];
  };
  verificationDetail?: {
    sentencesChecked?: number;
    numbersChecked?: number;
    numbersMatched?: number;
    droppedCount?: number;
    verdicts?: SentenceVerdictDetail[];
  };
  critiqueDetail?: {
    round?: number;
    issues?: ReviewIssueDetail[];
  };
  revisionDetail?: {
    round?: number;
    revisions?: SentenceRevisionDetail[];
  };
  reportId?: string | null;
  blockedDetail?: {
    message: string;
    suggestions?: string[];
  };
}

export interface LiveTailItem {
  tMs: number;
  formattedTime: string;
  agentId: StageAgentId;
  agentName: string;
  activity: string;
}

export interface ParticipatingAgentChip {
  id: StageAgentId;
  name: string;
  countLabel: string;
  state: StageAgentState;
}

export interface TimelineData {
  entries: TimelineEntry[];
  liveTail: LiveTailItem | null;
  participatingAgents: ParticipatingAgentChip[];
  isComplete: boolean;
  isBlocked: boolean;
  reportId: string | null;
}

export interface DeriveTimelineOptions {
  elapsedMs?: number;
  isStreaming?: boolean;
  isDisconnected?: boolean;
  reportId?: string | null;
}

function getAgentName(id: string | null | undefined): string {
  if (!id) return 'Hệ thống';
  if (id in STAGE_AGENTS) {
    return STAGE_AGENTS[id as StageAgentId].name;
  }
  return id;
}

function buildPlanProse(detail: Record<string, unknown>, planSummary?: LiveWorkStateInput['planSummary']): string {
  const rationale = (detail.rationale as string) || (detail.rationale_vi as string) || planSummary?.rationale;
  const questionType = (detail.question_type as string) || planSummary?.questionType;
  const typeLabel = questionType && QUESTION_TYPES[questionType] ? QUESTION_TYPES[questionType].toLowerCase() : 'phân tích';
  const entities = (detail.entities as string[]) || planSummary?.entities || [];
  const periods = (detail.periods as string[]) || planSummary?.periods || [];
  const metrics = (detail.metric_ids as string[]) || (detail.metrics as string[]) || planSummary?.metrics || [];

  const entityStr = entities.filter((e) => !e.startsWith('sector:')).join(' và ');
  const periodStr = periods.join(', ');

  if (rationale) {
    return `Mình đọc câu hỏi: đây là ${typeLabel}${entityStr ? ` giữa ${entityStr}` : ''}${periodStr ? `, kỳ ${periodStr}` : ''}. ${rationale}`;
  }

  const metricsCount = metrics.length > 0 ? `${metrics.length} chỉ tiêu` : 'các chỉ tiêu cần thiết';
  return `Mình đọc câu hỏi: đây là ${typeLabel}${entityStr ? ` giữa ${entityStr}` : ''}${periodStr ? `, kỳ ${periodStr}` : ''}. Mình giao việc cho chuyên viên tra cứu ${metricsCount}.`;
}

export function deriveTimeline(
  steps: TraceStep[],
  liveWorkState?: LiveWorkStateInput,
  options?: DeriveTimelineOptions
): TimelineData {
  const entries: TimelineEntry[] = [];
  const activeWriter = liveWorkState?.activeWriterRole as StageAgentId | null | undefined;
  const isStreaming = Boolean(options?.isStreaming);
  const nowMs = options?.elapsedMs ?? (steps.length > 0 ? steps[steps.length - 1].t_ms : 0);

  // Collect all sentence verdicts by role/sentence
  const verdictsBySentence = new Map<string, SentenceVerdictDetail>();
  if (liveWorkState?.verdictsByRole) {
    for (const vList of Object.values(liveWorkState.verdictsByRole)) {
      for (const v of vList) {
        if (v.sentence) {
          verdictsBySentence.set(v.sentence.trim(), v);
        }
      }
    }
  }

  for (const s of steps) {
    if (s.kind === 'verify' && Array.isArray(s.detail?.verdicts)) {
      for (const v of s.detail.verdicts as SentenceVerdictDetail[]) {
        if (v.sentence) {
          verdictsBySentence.set(v.sentence.trim(), v);
        }
      }
    }
  }

  // Iterate over chronological trace steps
  for (const step of steps) {
    const tMs = step.t_ms;
    const formattedTime = formatClock(tMs);
    const actor = step.actor as StageAgentId;
    const agentName = getAgentName(actor);

    switch (step.kind) {
      case 'plan': {
        const planDetail: PlanSummaryDetail = {
          questionType: (step.detail.question_type as string) || liveWorkState?.planSummary?.questionType,
          entities: (step.detail.entities as string[]) || liveWorkState?.planSummary?.entities,
          metrics: (step.detail.metric_ids as string[]) || (step.detail.metrics as string[]) || liveWorkState?.planSummary?.metrics,
          periods: (step.detail.periods as string[]) || liveWorkState?.planSummary?.periods,
          rationale: (step.detail.rationale as string) || liveWorkState?.planSummary?.rationale,
          planSummary: step.summary || liveWorkState?.planSummary?.planSummary
        };
        entries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: 'orchestrator',
          agentName: STAGE_AGENTS.orchestrator.name,
          kind: 'plan',
          prose: buildPlanProse(step.detail, liveWorkState?.planSummary),
          planDetail
        });
        break;
      }

      case 'tool_result': {
        const facts: SourcedFact[] = [];
        if (Array.isArray(step.detail.facts)) {
          for (const f of step.detail.facts as Array<Record<string, unknown>>) {
            facts.push({
              factId: String(f.fact_id || ''),
              label: String(f.label || ''),
              displayValue: String(f.display_value || f.value || ''),
              sourceNoteNo: typeof f.source_note_no === 'number' ? f.source_note_no : null,
              sourceLocator: (f.source_locator || f.source) as string | undefined
            });
          }
        }
        const resultCount = (step.detail.result_count as number) || facts.length;
        const toolName = (step.detail.label as string) || (step.detail.tool as string) || 'tra cứu số liệu';
        const durationMs = step.detail.duration_ms as number | undefined;

        entries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: actor,
          agentName,
          kind: 'data',
          prose: `Đã lấy ${resultCount} số liệu có nguồn từ phép phân tích ${toolName}.`,
          facts,
          toolDetail: {
            tool: (step.detail.tool as string) || 'tool',
            label: toolName,
            durationMs,
            resultCount
          }
        });
        break;
      }

      case 'draft': {
        let draftText = (step.detail.draft_text as string) || '';
        const sentenceVerdicts: SentenceVerdictDetail[] = [];
        if (Array.isArray(step.detail.sentences)) {
          const sentences = step.detail.sentences as Array<{ text?: string; sentence_id?: string }>;
          if (!draftText) {
            draftText = sentences.map((s) => s.text || '').filter(Boolean).join(' ');
          }
          for (const s of sentences) {
            if (s.text) {
              const matched = verdictsBySentence.get(s.text.trim());
              if (matched) {
                sentenceVerdicts.push(matched);
              }
            }
          }
        }

        entries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: actor,
          agentName,
          kind: 'draft',
          prose: 'Gửi bản nháp nhận định:',
          draftDetail: {
            text: draftText,
            isStreaming: false,
            verdicts: sentenceVerdicts.length > 0 ? sentenceVerdicts : undefined
          }
        });
        break;
      }

      case 'compose': {
        const draftText = (step.detail.draft_text as string) || '';
        const cleaned = readerText(draftText);
        entries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: 'orchestrator',
          agentName: STAGE_AGENTS.orchestrator.name,
          kind: 'draft',
          prose: 'Dựng bản nháp báo cáo tổng hợp:',
          draftDetail: {
            text: cleaned,
            isStreaming: false
          }
        });
        break;
      }

      case 'verify': {
        const sentencesChecked = Number(step.detail.sentences_checked) || 0;
        const numbersChecked = Number(step.detail.numbers_checked) || 0;
        const numbersMatched = Number(step.detail.numbers_matched) || 0;
        const droppedList = Array.isArray(step.detail.dropped) ? (step.detail.dropped as Array<{ reason?: string; explanation_vi?: string }>) : [];
        const droppedCount = droppedList.length;

        let prose = `Đối chiếu dữ liệu gốc: ${numbersMatched}/${numbersChecked} số liệu khớp.`;
        if (droppedCount > 0) {
          prose += ` Phát hiện ${droppedCount} điểm sai lệch và đã loại câu vi phạm.`;
        } else {
          prose += ' Tất cả câu đều đạt yêu cầu kiểm tra.';
        }

        const verdicts: SentenceVerdictDetail[] = [];
        if (Array.isArray(step.detail.verdicts)) {
          verdicts.push(...(step.detail.verdicts as SentenceVerdictDetail[]));
        }

        entries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: 'verifier',
          agentName: STAGE_AGENTS.verifier.name,
          kind: 'verification',
          prose,
          verificationDetail: {
            sentencesChecked,
            numbersChecked,
            numbersMatched,
            droppedCount,
            verdicts
          }
        });
        break;
      }

      case 'critique_issue': {
        const round = (step.detail.round as number) || 1;
        const desc = (step.detail.description as string) || step.summary || 'Yêu cầu rà soát lập luận';
        const cleanedDesc = readerText(desc.replace(/^Yêu cầu sửa:\s*/i, ''));

        entries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: 'critic',
          agentName: STAGE_AGENTS.critic.name,
          kind: 'critique',
          prose: `Mình yêu cầu sửa (vòng ${round}): ${cleanedDesc}`,
          critiqueDetail: {
            round,
            issues: [
              {
                round,
                issueType: step.detail.issue_type as string | undefined,
                severity: step.detail.severity as string | undefined,
                description: cleanedDesc,
                requiredAction: step.detail.required_action as string | undefined
              }
            ]
          }
        });
        break;
      }

      case 'revision': {
        const round = (step.detail.round as number) || 1;
        const after = (step.detail.after as string) || (step.detail.draft_text as string) || step.summary || '';
        const cleanedAfter = readerText(after);

        entries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: actor,
          agentName,
          kind: 'revision',
          prose: `Đã sửa theo phản biện (vòng ${round}): ${cleanedAfter}`,
          revisionDetail: {
            round,
            revisions: [
              {
                round,
                before: step.detail.before as string | undefined,
                after: cleanedAfter,
                verified: Boolean(step.detail.verified)
              }
            ]
          }
        });
        break;
      }

      case 'accept': {
        const round = (step.detail.round as number) || 2;
        entries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: 'critic',
          agentName: STAGE_AGENTS.critic.name,
          kind: 'accept',
          prose: `Vòng ${round}: Hoàn tất kiểm tra chéo và rà soát báo cáo.`
        });
        break;
      }

      case 'report_ready': {
        const reportId = (step.detail.report_id as string) || options?.reportId || null;
        entries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: 'system',
          agentName: 'Hệ thống',
          kind: 'complete',
          prose: 'Báo cáo sẵn sàng.',
          reportId
        });
        break;
      }

      case 'blocked': {
        const message = (step.detail.message as string) || step.summary || 'Yêu cầu nằm ngoài phạm vi phân tích.';
        entries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: 'system',
          agentName: 'Hệ thống',
          kind: 'blocked',
          prose: message,
          blockedDetail: {
            message,
            suggestions: (step.detail.suggestions as string[]) || undefined
          }
        });
        break;
      }

      default:
        // Other steps (e.g. assign) are covered by the story narrative
        break;
    }
  }

  // Handle active streaming draft delta if any
  const hasCompletedDraftOrComposeForWriter = (role: StageAgentId) => {
    return steps.some(
      (s) =>
        (s.actor === role && s.kind === 'draft') ||
        (role === 'orchestrator' && s.kind === 'compose')
    );
  };

  if (activeWriter && liveWorkState?.draftsByRole?.[activeWriter] && isStreaming) {
    const streamingText = liveWorkState.draftsByRole[activeWriter];
    // If no finished step exists yet for this draft in the current stage, show streaming entry
    if (!hasCompletedDraftOrComposeForWriter(activeWriter)) {
      entries.push({
        id: `live-draft-${activeWriter}`,
        tMs: nowMs,
        formattedTime: formatClock(nowMs),
        agentId: activeWriter,
        agentName: getAgentName(activeWriter),
        kind: 'draft',
        prose: 'Bản nháp nhận định (đang viết):',
        draftDetail: {
          text: streamingText,
          isStreaming: true
        }
      });
    }
  }

  // Check terminal states
  const isComplete = steps.some((s) => s.kind === 'report_ready') || Boolean(options?.reportId);
  const isBlocked = steps.some((s) => s.kind === 'blocked') || Boolean(liveWorkState?.isBlocked);

  // If blocked from liveWorkState without step
  if (isBlocked && !entries.some((e) => e.kind === 'blocked')) {
    const blockedMsg = liveWorkState?.blockedInfo?.message || 'Yêu cầu nằm ngoài phạm vi phân tích.';
    entries.push({
      id: 'blocked-terminal',
      tMs: nowMs,
      formattedTime: formatClock(nowMs),
      agentId: 'system',
      agentName: 'Hệ thống',
      kind: 'blocked',
      prose: blockedMsg,
      blockedDetail: {
        message: blockedMsg,
        suggestions: liveWorkState?.blockedInfo?.suggestions
      }
    });
  }

  // If completed with reportId but without step
  if (isComplete && !entries.some((e) => e.kind === 'complete')) {
    entries.push({
      id: 'report-ready-terminal',
      tMs: nowMs,
      formattedTime: formatClock(nowMs),
      agentId: 'system',
      agentName: 'Hệ thống',
      kind: 'complete',
      prose: 'Báo cáo sẵn sàng.',
      reportId: options?.reportId || null
    });
  }

  // Live Tail Item:
  // "Cái duy nhất 'chưa xong' là một dòng trực tiếp ở cuối: chấm nhấp nháy, tên agent đang làm, việc đang làm và đồng hồ chạy"
  let liveTail: LiveTailItem | null = null;
  if (isStreaming && !isComplete && !isBlocked && !options?.isDisconnected) {
    // Check if any tool is currently running
    let runningAgent: StageAgentId | null = null;
    let runningActivity = '';

    if (liveWorkState?.toolCallsByRole) {
      for (const [role, tList] of Object.entries(liveWorkState.toolCallsByRole)) {
        const runningTool = tList.find((t) => t.status === 'running');
        if (runningTool) {
          runningAgent = role as StageAgentId;
          runningActivity = `Đang tra cứu dữ liệu (${runningTool.tool})...`;
          break;
        }
      }
    }

    if (!runningAgent && activeWriter) {
      runningAgent = activeWriter;
      runningActivity = 'Đang viết nhận định...';
    }

    if (!runningAgent) {
      // Find the last participating agent or orchestrator
      const lastStep = steps[steps.length - 1];
      if (lastStep && lastStep.actor in STAGE_AGENTS) {
        runningAgent = lastStep.actor as StageAgentId;
        runningActivity = 'Đang xử lý tiếp...';
      } else {
        runningAgent = 'orchestrator';
        runningActivity = 'Đang lập kế hoạch...';
      }
    }

    liveTail = {
      tMs: nowMs,
      formattedTime: formatClock(nowMs),
      agentId: runningAgent,
      agentName: getAgentName(runningAgent),
      activity: runningActivity
    };
  }

  // Participating Agents chips
  // "Agent không tham gia không hiện."
  const participatingIds = new Set<StageAgentId>();
  for (const s of steps) {
    if (s.actor in STAGE_AGENTS) {
      participatingIds.add(s.actor as StageAgentId);
    }
    if (s.recipient && s.recipient in STAGE_AGENTS) {
      participatingIds.add(s.recipient as StageAgentId);
    }
  }
  if (activeWriter && activeWriter in STAGE_AGENTS) {
    participatingIds.add(activeWriter);
  }

  // Always include orchestrator if any step exists
  if (steps.length > 0) {
    participatingIds.add('orchestrator');
  }

  const participatingAgents: ParticipatingAgentChip[] = [];
  const AGENT_ORDER: StageAgentId[] = ['orchestrator', 'company', 'sector', 'macro', 'verifier', 'critic'];

  for (const id of AGENT_ORDER) {
    if (participatingIds.has(id)) {
      let countLabel = '';
      if (id === 'company' || id === 'sector' || id === 'macro') {
        const findingsCount = entries.filter((e) => e.agentId === id && e.kind === 'draft').length;
        const dataCount = entries.filter((e) => e.agentId === id && e.kind === 'data').length;
        if (findingsCount > 0) {
          countLabel = `${findingsCount} nhận định`;
        } else if (dataCount > 0) {
          countLabel = `${dataCount} tra cứu`;
        }
      } else if (id === 'verifier') {
        const vEntry = entries.find((e) => e.kind === 'verification');
        if (vEntry?.verificationDetail?.numbersChecked) {
          countLabel = `${vEntry.verificationDetail.numbersChecked} số liệu`;
        }
      } else if (id === 'critic') {
        const cEntries = entries.filter((e) => e.kind === 'critique');
        if (cEntries.length > 0) {
          countLabel = `${cEntries.length} góp ý`;
        }
      }

      let state: StageAgentState = 'idle';
      if (isComplete) {
        state = 'done';
      } else if (isBlocked) {
        state = 'blocked';
      } else if (liveTail?.agentId === id) {
        state = 'busy';
      } else if (entries.some((e) => e.agentId === id)) {
        state = 'done';
      }

      participatingAgents.push({
        id,
        name: STAGE_AGENTS[id].name,
        countLabel,
        state
      });
    }
  }

  return {
    entries,
    liveTail,
    participatingAgents,
    isComplete,
    isBlocked,
    reportId: options?.reportId || null
  };
}
