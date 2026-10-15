import type { TraceStep } from './types';
import {
  STAGE_AGENTS,
  QUESTION_TYPES,
  readerText,
  type StageAgentId,
  type StageAgentState,
  type SourcedFact,
  type SentenceVerdictDetail,
  type ReviewIssueDetail,
  type SentenceRevisionDetail,
  type PlanSummaryDetail,
  type LiveWorkStateInput
} from './agentStage';
import { fmtPeriod } from '@/shared/lib/formatting';

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
  ariaName: string;
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

export const TOOL_VI_LABELS: Record<string, string> = {
  head_to_head: 'so sánh đối đầu',
  lookup: 'tra cứu',
  trend: 'xu hướng',
  company_profile: 'hồ sơ doanh nghiệp',
  ranking: 'xếp hạng',
  decomposition: 'phân rã chỉ tiêu',
  sector_peer_position: 'vị thế nhóm ngành',
  peer_comparison: 'so sánh nhóm',
  financial_ratio: 'tỷ số tài chính',
  semantic_critique: 'phản biện lập luận',
  query_metric_observations: 'truy vấn số liệu',
  query_observations: 'truy vấn số liệu',
  query_facts: 'truy vấn dữ kiện',
  calculate_peer_rankings: 'xếp hạng nhóm ngành'
};

export function translateToolName(tool?: string): string {
  if (!tool) return 'tra cứu số liệu';
  const clean = tool.toLowerCase().trim();
  if (clean in TOOL_VI_LABELS) return TOOL_VI_LABELS[clean];
  return clean.replace(/_/g, ' ');
}

export const ROLE_DISPLAY_NAMES: Record<string, string> = {
  orchestrator: 'Điều phối viên',
  company: 'Chuyên viên doanh nghiệp',
  sector: 'Chuyên viên ngành',
  macro: 'Chuyên viên vĩ mô',
  specialist: 'Chuyên viên doanh nghiệp',
  verifier: 'Kiểm tra số liệu',
  critic: 'Phản biện',
  system: 'Hệ thống'
};

export function getAgentName(id: string | null | undefined): string {
  if (!id) return 'Hệ thống';
  if (id in ROLE_DISPLAY_NAMES) return ROLE_DISPLAY_NAMES[id];
  if (id in STAGE_AGENTS) return STAGE_AGENTS[id as StageAgentId].name;
  return 'Chuyên viên';
}

export const VERDICT_REASON_VI_LABELS: Record<string, string> = {
  comparison_direction_mismatch: 'Chiều so sánh không khớp dữ liệu',
  number_mismatch: 'Số liệu không khớp dữ liệu gốc',
  unresolved_critique: 'Chưa giải quyết phản biện',
  unsupported_claim: 'Nhận định không có bằng chứng hỗ trợ',
  missing_source_locator: 'Thiếu định vị nguồn gốc',
  scope_unsupported: 'Phạm vi phân tích chưa được hỗ trợ'
};

export function translateDropReason(reason?: string | null): string {
  if (!reason) return 'số liệu không khớp';
  if (reason in VERDICT_REASON_VI_LABELS) return VERDICT_REASON_VI_LABELS[reason];
  return reason.replace(/_/g, ' ');
}

export function scrubInternalIdentifiers(text: string): string {
  if (!text) return '';
  return text
    // Replace raw periods
    .replace(/\bkỳ\s+(\d{4})_Q([1-4])\b/gi, (_match, y, q) => `Quý ${q}/${y}`)
    .replace(/\b(\d{4})_Q([1-4])\b/gi, (_match, y, q) => `Quý ${q}/${y}`)
    .replace(/\bQ([1-4])_(\d{4})\b/gi, (_match, q, y) => `Quý ${q}/${y}`)
    .replace(/\b(\d{4})Q([1-4])\b/gi, (_match, y, q) => `Quý ${q}/${y}`)
    // Replace tool identifiers
    .replace(/\bhead_to_head\b/gi, 'so sánh đối đầu')
    .replace(/\bcompany_profile\b/gi, 'hồ sơ doanh nghiệp')
    .replace(/\bsector_peer_position\b/gi, 'vị thế nhóm ngành')
    .replace(/\bpeer_comparison\b/gi, 'so sánh nhóm')
    .replace(/\blookup\b/gi, 'tra cứu')
    .replace(/\branking\b/gi, 'xếp hạng')
    .replace(/\bdecomposition\b/gi, 'phân rã chỉ tiêu')
    .replace(/\bfinancial_ratio\b/gi, 'tỷ số tài chính')
    .replace(/\bsemantic_critique\b/gi, 'phản biện lập luận')
    .replace(/\bsector:bank\b/gi, 'toàn ngành ngân hàng')
    // Drop fact_ids and markers
    .replace(/\s*\bfact_ids\b\s*/gi, ' ')
    .replace(/\s*\bfact:[\w:.-]+\b\s*/gi, ' ')
    .replace(/\s*\b(?:sent|blk|block)[-:][\w.-]+\b\s*/gi, ' ')
    .replace(/\s*\b(?:sent|blk)-[a-z0-9-]+\b\s*/gi, ' ')
    .replace(/\s*\b(?:report_level_synthesis|report_level)\b\s*/gi, ' ')
    .replace(/\s*\((?:sent|fact|blk|block)[-:][^)]*\)/gi, '')
    // Clean any residual snake_case words (assert no /[a-z]+_[a-z_]+/)
    .replace(/\b([a-z]+)_([a-z0-9_]+)\b/gi, (_match, p1, p2) => `${p1} ${p2.replace(/_/g, ' ')}`)
    .replace(/\s{2,}/g, ' ')
    .replace(/\s+([.,;:])/g, '$1')
    .trim();
}

export function cleanCriticIssueText(desc: string, severity?: string): string {
  if (!desc) return 'Phản biện yêu cầu rà soát và hoàn thiện báo cáo.';
  const hasSnakeCase = /[a-z]+_[a-z0-9_]+/i.test(desc);
  const severitySuffix = severity ? ` (Mức độ: ${severity === 'MAJOR' ? 'Quan trọng' : severity})` : '';

  if (hasSnakeCase || /headline|report_level|block/i.test(desc)) {
    if (/headline|mở đầu|khởi đầu|report_level/i.test(desc)) {
      return `Phản biện yêu cầu sửa phần mở đầu của báo cáo.${severitySuffix}`;
    }
    return `Phản biện yêu cầu rà soát lập luận và hoàn thiện báo cáo.${severitySuffix}`;
  }

  const cleaned = scrubInternalIdentifiers(readerText(desc.replace(/^Yêu cầu sửa:\s*/i, '')));
  return `${cleaned}${severitySuffix}`;
}

export function cleanOrchestratorDraftText(raw: string): string {
  if (!raw) return '';
  const cleaned = scrubInternalIdentifiers(raw);
  const sentences = cleaned
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 5);

  const uniqueSentences: string[] = [];
  for (const s of sentences) {
    if (!uniqueSentences.some((u) => u.toLowerCase() === s.toLowerCase())) {
      uniqueSentences.push(s);
    }
  }
  return uniqueSentences.join(' ');
}

function buildPlanProse(detail?: Record<string, unknown>, planSummary?: LiveWorkStateInput['planSummary']): string {
  const rawRationale = (detail?.rationale as string) || (detail?.rationale_vi as string) || planSummary?.rationale;
  const rationale = rawRationale ? scrubInternalIdentifiers(rawRationale) : undefined;
  const questionType = (detail?.question_type as string) || planSummary?.questionType;
  const typeLabel = questionType && QUESTION_TYPES[questionType] ? QUESTION_TYPES[questionType].toLowerCase() : 'phân tích';
  const entities = (detail?.entities as string[]) || planSummary?.entities || [];
  const periods = (detail?.periods as string[]) || planSummary?.periods || [];
  const metrics = (detail?.metric_ids as string[]) || (detail?.metrics as string[]) || planSummary?.metrics || [];

  const entityStr = entities
    .filter((e) => !e.startsWith('sector:'))
    .map((e) => scrubInternalIdentifiers(e))
    .join(' và ');
  const periodStr = periods.map((p) => fmtPeriod(p)).filter(Boolean).join(', ');
  const periodPart = periodStr ? (/^quý/i.test(periodStr) ? `, ${periodStr}` : `, kỳ ${periodStr}`) : '';

  if (rationale) {
    return `Mình đọc câu hỏi: đây là ${typeLabel}${entityStr ? ` giữa ${entityStr}` : ''}${periodPart}. ${rationale}`;
  }

  const metricsCount = metrics.length > 0 ? `${metrics.length} chỉ tiêu` : 'các chỉ tiêu cần thiết';
  return `Mình đọc câu hỏi: đây là ${typeLabel}${entityStr ? ` giữa ${entityStr}` : ''}${periodPart}. Mình giao việc cho chuyên viên tra cứu ${metricsCount}.`;
}

export function deriveTimeline(
  steps: TraceStep[],
  liveWorkState?: LiveWorkStateInput,
  options?: DeriveTimelineOptions
): TimelineData {
  const rawEntries: TimelineEntry[] = [];
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
      for (const rawV of s.detail.verdicts as Array<Record<string, unknown>>) {
        if (rawV.sentence) {
          const v: SentenceVerdictDetail = {
            sentence: scrubInternalIdentifiers(String(rawV.sentence)),
            verdict: (rawV.verdict as 'kept' | 'dropped') || 'kept',
            dropReason: rawV.dropReason ? translateDropReason(String(rawV.dropReason)) : (rawV.drop_reason ? translateDropReason(String(rawV.drop_reason)) : undefined),
            explanationVi: (rawV.explanationVi || rawV.explanation_vi) ? scrubInternalIdentifiers(String(rawV.explanationVi || rawV.explanation_vi)) : undefined,
            factIds: (rawV.factIds || rawV.fact_ids) as string[] | undefined
          };
          verdictsBySentence.set(v.sentence.trim(), v);
        }
      }
    }
  }

  // Iterate over chronological trace steps
  for (const step of steps) {
    const tMs = step.t_ms;
    const formattedTime = formatClock(tMs);
    const actor = ((step.actor as string) === 'specialist' ? 'company' : step.actor) as StageAgentId;
    const agentName = getAgentName(step.actor);

    switch (step.kind) {
      case 'plan': {
        const rawPeriods = (step.detail?.periods as string[]) || liveWorkState?.planSummary?.periods;
        const rawEntities = (step.detail?.entities as string[]) || liveWorkState?.planSummary?.entities;
        const planDetail: PlanSummaryDetail = {
          questionType: (step.detail?.question_type as string) || liveWorkState?.planSummary?.questionType,
          entities: rawEntities ? rawEntities.map((e) => scrubInternalIdentifiers(e)) : undefined,
          metrics: (step.detail?.metric_ids as string[]) || (step.detail?.metrics as string[]) || liveWorkState?.planSummary?.metrics,
          periods: rawPeriods ? rawPeriods.map((p) => fmtPeriod(p)).filter(Boolean) : undefined,
          rationale: (step.detail?.rationale as string) || liveWorkState?.planSummary?.rationale,
          planSummary: step.summary || liveWorkState?.planSummary?.planSummary
        };
        rawEntries.push({
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
              label: scrubInternalIdentifiers(String(f.label || '')),
              displayValue: scrubInternalIdentifiers(String(f.display_value || f.value || '')),
              sourceNoteNo: typeof f.source_note_no === 'number' ? f.source_note_no : null,
              sourceLocator: (f.source_locator || f.source) as string | undefined
            });
          }
        }
        const resultCount = (step.detail.result_count as number) || facts.length;
        const rawTool = (step.detail.tool as string) || '';
        const toolLabel = (step.detail.label as string) || translateToolName(rawTool);
        const cleanToolLabel = scrubInternalIdentifiers(toolLabel);
        const durationMs = step.detail.duration_ms as number | undefined;

        rawEntries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: actor,
          agentName,
          kind: 'data',
          prose: `Đã lấy ${resultCount} số liệu có nguồn từ phép phân tích ${cleanToolLabel}.`,
          facts,
          toolDetail: {
            tool: rawTool || 'tool',
            label: cleanToolLabel,
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

        const cleanedDraftText = scrubInternalIdentifiers(draftText);
        rawEntries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: actor,
          agentName,
          kind: 'draft',
          prose: 'Gửi bản nháp nhận định:',
          draftDetail: {
            text: cleanedDraftText,
            isStreaming: false,
            verdicts: sentenceVerdicts.length > 0 ? sentenceVerdicts : undefined
          }
        });
        break;
      }

      case 'compose': {
        const draftText = (step.detail.draft_text as string) || '';
        const cleaned = cleanOrchestratorDraftText(draftText);
        rawEntries.push({
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
          for (const rawV of step.detail.verdicts as Array<Record<string, unknown>>) {
            verdicts.push({
              sentence: scrubInternalIdentifiers(String(rawV.sentence || '')),
              verdict: (rawV.verdict as 'kept' | 'dropped') || 'kept',
              dropReason: rawV.dropReason ? translateDropReason(String(rawV.dropReason)) : (rawV.drop_reason ? translateDropReason(String(rawV.drop_reason)) : undefined),
              explanationVi: (rawV.explanationVi || rawV.explanation_vi) ? scrubInternalIdentifiers(String(rawV.explanationVi || rawV.explanation_vi)) : undefined,
              factIds: (rawV.factIds || rawV.fact_ids) as string[] | undefined
            });
          }
        }

        rawEntries.push({
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
        const severity = (step.detail.severity as string) || undefined;
        const cleanedDesc = cleanCriticIssueText(desc, severity);

        rawEntries.push({
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
                issueType: step.detail.issue_type ? scrubInternalIdentifiers(String(step.detail.issue_type)) : undefined,
                severity,
                description: cleanedDesc,
                requiredAction: step.detail.required_action ? scrubInternalIdentifiers(String(step.detail.required_action)) : undefined
              }
            ]
          }
        });
        break;
      }

      case 'revision': {
        const round = (step.detail.round as number) || 1;
        const after = (step.detail.after as string) || (step.detail.draft_text as string) || step.summary || '';
        const cleanedAfter = scrubInternalIdentifiers(readerText(after));

        rawEntries.push({
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
                before: step.detail.before ? scrubInternalIdentifiers(String(step.detail.before)) : undefined,
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
        rawEntries.push({
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
        rawEntries.push({
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
        const cleanMessage = scrubInternalIdentifiers(message);
        rawEntries.push({
          id: step.step_id,
          tMs,
          formattedTime,
          agentId: 'system',
          agentName: 'Hệ thống',
          kind: 'blocked',
          prose: cleanMessage,
          blockedDetail: {
            message: cleanMessage,
            suggestions: (step.detail.suggestions as string[]) || undefined
          }
        });
        break;
      }

      default:
        break;
    }
  }

  const hasCompletedDraftOrComposeForWriter = (role: StageAgentId) => {
    return steps.some(
      (s) =>
        (s.actor === role && s.kind === 'draft') ||
        (role === 'orchestrator' && s.kind === 'compose')
    );
  };

  // Handle live tool calls from liveWorkState ONLY if not already represented in rawEntries
  if (liveWorkState?.toolCallsByRole) {
    for (const [rawRole, tList] of Object.entries(liveWorkState.toolCallsByRole)) {
      const role = (rawRole === 'specialist' ? 'company' : rawRole) as StageAgentId;
      for (const t of tList) {
        const toolLabel = translateToolName(t.tool);
        const alreadyInEntries = rawEntries.some(
          (e) =>
            e.kind === 'data' &&
            (e.toolDetail?.tool === t.tool || e.toolDetail?.label === toolLabel || e.toolDetail?.label === t.tool)
        );
        if (!alreadyInEntries) {
          const rawFacts: SourcedFact[] = Array.isArray(t.facts) ? t.facts : [];
          const facts: SourcedFact[] = rawFacts.map((f) => ({
            ...f,
            label: scrubInternalIdentifiers(f.label),
            displayValue: scrubInternalIdentifiers(f.displayValue)
          }));
          rawEntries.push({
            id: `live-tool-${role}-${t.tool}`,
            tMs: nowMs,
            formattedTime: formatClock(nowMs),
            agentId: role,
            agentName: getAgentName(role),
            kind: 'data',
            prose: `Đã lấy ${t.resultCount ?? 0} số liệu có nguồn từ phép phân tích ${toolLabel}.`,
            facts,
            toolDetail: {
              tool: t.tool,
              label: toolLabel,
              durationMs: t.durationMs,
              resultCount: t.resultCount
            }
          });
        }
      }
    }
  }

  if (liveWorkState?.draftsByRole) {
    for (const [rawRole, dText] of Object.entries(liveWorkState.draftsByRole)) {
      const role = (rawRole === 'specialist' ? 'company' : rawRole) as StageAgentId;
      if (
        dText &&
        !hasCompletedDraftOrComposeForWriter(role) &&
        !rawEntries.some((e) => (e.agentId === role || e.agentId === rawRole) && e.kind === 'draft')
      ) {
        const sentenceVerdicts: SentenceVerdictDetail[] = [];
        const roleVerdicts = liveWorkState?.verdictsByRole?.[rawRole] || liveWorkState?.verdictsByRole?.[role] || [];
        for (const rv of roleVerdicts) {
          sentenceVerdicts.push({
            sentence: scrubInternalIdentifiers(rv.sentence),
            verdict: rv.verdict,
            dropReason: rv.dropReason ? translateDropReason(rv.dropReason) : undefined,
            explanationVi: rv.explanationVi ? scrubInternalIdentifiers(rv.explanationVi) : (rv.verdict === 'kept' ? 'Khớp dữ liệu gốc' : 'Bị loại'),
            factIds: rv.factIds
          });
        }

        const cleanedDText = scrubInternalIdentifiers(dText);
        rawEntries.push({
          id: `live-draft-${role}`,
          tMs: nowMs,
          formattedTime: formatClock(nowMs),
          agentId: role,
          agentName: getAgentName(role),
          kind: 'draft',
          prose: 'Bản nháp nhận định:',
          draftDetail: {
            text: cleanedDText,
            isStreaming: activeWriter === role || activeWriter === rawRole,
            verdicts: sentenceVerdicts.length > 0 ? sentenceVerdicts : undefined
          }
        });
      }
    }
  }

  // Check terminal states
  const isComplete = steps.some((s) => s.kind === 'report_ready') || Boolean(options?.reportId);
  const isBlocked = steps.some((s) => s.kind === 'blocked') || Boolean(liveWorkState?.isBlocked);

  // If blocked from liveWorkState without step
  if (isBlocked && !rawEntries.some((e) => e.kind === 'blocked')) {
    const rawMsg = liveWorkState?.blockedInfo?.message || 'Yêu cầu nằm ngoài phạm vi phân tích.';
    const blockedMsg = scrubInternalIdentifiers(rawMsg);
    rawEntries.push({
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
  if (isComplete && !rawEntries.some((e) => e.kind === 'complete')) {
    rawEntries.push({
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

  // DE-DUPLICATION AND STRICT TERMINAL ORDERING:
  // 1. Exactly ONE entry per logical data event (same tool)
  // 2. Exactly ONE complete entry (never duplicate "Báo cáo sẵn sàng")
  // 3. NOTHING may come after the final "Báo cáo sẵn sàng" entry!
  const entries: TimelineEntry[] = [];
  let sawComplete = false;

  for (const entry of rawEntries) {
    if (sawComplete) {
      // Nothing may appear after complete!
      break;
    }

    if (entry.kind === 'complete') {
      if (!sawComplete) {
        entries.push(entry);
        sawComplete = true;
      }
      continue;
    }

    if (entry.kind === 'data') {
      const alreadyHas = entries.some(
        (e) =>
          e.kind === 'data' &&
          (e.toolDetail?.tool === entry.toolDetail?.tool ||
            (entry.toolDetail?.label && e.toolDetail?.label === entry.toolDetail.label))
      );
      if (alreadyHas) continue;
    }

    entries.push(entry);
  }

  // Live Tail Item:
  // "Cái duy nhất 'chưa xong' là một dòng trực tiếp ở cuối: chấm nhấp nháy, tên agent đang làm, việc đang làm và đồng hồ chạy"
  let liveTail: LiveTailItem | null = null;
  if (isStreaming && !isComplete && !isBlocked && !options?.isDisconnected) {
    let runningAgent: StageAgentId | null = null;
    let runningActivity = '';

    if (liveWorkState?.toolCallsByRole) {
      for (const [rawRole, tList] of Object.entries(liveWorkState.toolCallsByRole)) {
        const role = (rawRole === 'specialist' ? 'company' : rawRole) as StageAgentId;
        const runningTool = tList.find((t) => t.status === 'running');
        if (runningTool) {
          runningAgent = role;
          const toolLabel = translateToolName(runningTool.tool);
          runningActivity = `Đang tra cứu dữ liệu (${toolLabel})...`;
          break;
        }
      }
    }

    if (!runningAgent && activeWriter) {
      const writer = ((activeWriter as string) === 'specialist' ? 'company' : activeWriter) as StageAgentId;
      runningAgent = writer;
      runningActivity = 'Đang viết nhận định...';
    }

    if (!runningAgent) {
      const lastStep = steps[steps.length - 1];
      if (lastStep && (lastStep.actor in STAGE_AGENTS || lastStep.actor in ROLE_DISPLAY_NAMES)) {
        const actor = ((lastStep.actor as string) === 'specialist' ? 'company' : lastStep.actor) as StageAgentId;
        runningAgent = actor;
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
  // Defect 5: "Show chips only for agents that actually have at least one event."
  // Defect 5: "Counts like '(1 nhận định)' next to 'Chuyên viên doanh nghiệp' contradict '4 nhận định' elsewhere: derive from the same selector."
  const participatingIds = new Set<StageAgentId>();

  // Always include orchestrator if entries exist
  if (entries.length > 0) {
    participatingIds.add('orchestrator');
  }

  for (const e of entries) {
    if (e.agentId in STAGE_AGENTS) {
      participatingIds.add(e.agentId as StageAgentId);
    }
  }

  if (liveTail && liveTail.agentId in STAGE_AGENTS) {
    participatingIds.add(liveTail.agentId);
  }

  const participatingAgents: ParticipatingAgentChip[] = [];
  const AGENT_ORDER: StageAgentId[] = ['orchestrator', 'company', 'sector', 'macro', 'verifier', 'critic'];

  for (const id of AGENT_ORDER) {
    if (participatingIds.has(id)) {
      let countLabel = '';
      if (id === 'company' || id === 'sector' || id === 'macro') {
        let sentenceCount = 0;
        for (const e of entries) {
          if (e.agentId === id && e.kind === 'draft') {
            if (e.draftDetail?.verdicts && e.draftDetail.verdicts.length > 0) {
              sentenceCount += e.draftDetail.verdicts.length;
            } else if (e.draftDetail?.text) {
              const sList = e.draftDetail.text.split(/(?<=[.!?])\s+/).filter((s) => s.trim().length > 5);
              sentenceCount += Math.max(1, sList.length);
            }
          }
        }

        if (sentenceCount > 0) {
          countLabel = `${sentenceCount} nhận định`;
        } else {
          const dataCount = entries.filter((e) => e.agentId === id && e.kind === 'data').length;
          if (dataCount > 0) {
            countLabel = `${dataCount} tra cứu`;
          }
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
        ariaName: STAGE_AGENTS[id].ariaName,
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
