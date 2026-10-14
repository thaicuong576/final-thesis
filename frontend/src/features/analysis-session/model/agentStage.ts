import type { TraceStep } from './types';

/** Agents drawn on the live stage. `verifier` is the deterministic number checker. */
export type StageAgentId = 'orchestrator' | 'sector' | 'company' | 'macro' | 'verifier' | 'critic';
export type StageAgentState = 'idle' | 'busy' | 'fixing' | 'done' | 'unused';

export interface StageAgent {
  id: StageAgentId;
  /** Accessible name, kept stable for tests and screen readers. */
  ariaName: string;
  name: string;
  role: string;
  side: 'center' | 'left' | 'right';
}

export const STAGE_AGENTS: Record<StageAgentId, StageAgent> = {
  orchestrator: { id: 'orchestrator', ariaName: 'Điều phối viên', name: 'Điều phối viên', role: 'Lập kế hoạch · giao việc · lắp báo cáo', side: 'center' },
  sector: { id: 'sector', ariaName: 'Sector', name: 'Chuyên viên ngành', role: 'So sánh với nhóm ngân hàng', side: 'left' },
  company: { id: 'company', ariaName: 'Company', name: 'Chuyên viên doanh nghiệp', role: 'Số liệu và diễn biến của ngân hàng', side: 'left' },
  macro: { id: 'macro', ariaName: 'Macro', name: 'Chuyên viên vĩ mô', role: 'Bối cảnh kinh tế', side: 'left' },
  verifier: { id: 'verifier', ariaName: 'Kiểm tra số liệu', name: 'Kiểm tra số liệu', role: 'Đối chiếu từng con số với dữ liệu gốc', side: 'right' },
  critic: { id: 'critic', ariaName: 'Phản biện', name: 'Phản biện', role: 'Rà soát lập luận, yêu cầu sửa', side: 'right' }
};

export interface AgentSnapshot {
  state: StageAgentState;
  activity: string;
  /** Run-relative time (ms) the current activity started. */
  sinceMs: number;
  stats: string[];
  summaryLine: string;
}

export const PHASES = ['Lập kế hoạch', 'Thu thập số liệu', 'Viết nhận định', 'Kiểm tra số liệu', 'Phản biện', 'Hoàn tất'] as const;

export const QUESTION_TYPES: Record<string, string> = {
  lookup: 'Tra cứu nhanh',
  company_profile: 'Hồ sơ doanh nghiệp',
  ranking: 'Xếp hạng',
  trend: 'Xu hướng',
  head_to_head: 'So sánh đối đầu',
  sector_theme: 'Toàn ngành',
  relationship: 'Tương quan'
};

const KIND_PHASE: Partial<Record<TraceStep['kind'], number>> = {
  plan: 0,
  assign: 1,
  tool_result: 1,
  draft: 2,
  verify: 3,
  compose: 4,
  critique_issue: 4,
  revision: 4,
  accept: 4,
  cross_level_finding: 4,
  report_ready: 5
};

/** Remove internal identifiers that the critic sometimes quotes (sentence ids, fact ids). */
export function readerText(text: string): string {
  return text
    .replace(/\s*\((?:sent|fact|blk|block)[-:][^)]*\)/gi, '')
    .replace(/\b(?:sent|blk)-[a-z0-9-]+\b/gi, '')
    .replace(/\bfact:[\w:.-]+/gi, '')
    .replace(/\s{2,}/g, ' ')
    .replace(/\s+([.,;:])/g, '$1')
    .trim();
}

function asCount(value: unknown): number | null {
  if (Array.isArray(value)) return value.length;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  return null;
}

function isStageAgent(id: string | null | undefined): id is StageAgentId {
  return Boolean(id && id in STAGE_AGENTS);
}

export interface StageModel {
  agents: StageAgentId[];
  snapshots: Record<StageAgentId, AgentSnapshot>;
  phase: number;
  done: boolean;
  questionType?: string;
}

/**
 * Derive who is working right now from the revealed prefix of the trace. The trace only records
 * hand-offs, so the stage infers the busy agent between them: an assignee works until it replies,
 * a specialist that returned data is drafting until its draft arrives, and so on.
 */
export function deriveStage(
  steps: TraceStep[],
  allSteps?: TraceStep[],
  liveWorkState?: {
    draftsByRole?: Record<string, string>;
    toolCallsByRole?: Record<string, unknown>;
    verdictsByRole?: Record<string, unknown>;
    reviewIssues?: Array<unknown>;
    revisions?: Array<unknown>;
    planSummary?: { specialistsCalled?: string[] };
  }
): StageModel {
  const full = allSteps && allSteps.length > 0 ? allSteps : steps;
  const plan = full.find((s) => s.kind === 'plan') || steps.find((s) => s.kind === 'plan');
  const planned = ((plan?.detail?.agents as Array<{ agent: string; decision: string }> | undefined) || [])
    .filter((a) => a.decision === 'run')
    .map((a) => a.agent.toLowerCase());

  const seen = new Set<StageAgentId>(['orchestrator']);
  for (const id of planned) if (isStageAgent(id)) seen.add(id);
  if (liveWorkState?.planSummary?.specialistsCalled) {
    for (const id of liveWorkState.planSummary.specialistsCalled) {
      const lower = id.toLowerCase();
      if (isStageAgent(lower)) seen.add(lower);
    }
  }
  for (const s of steps) {
    if (isStageAgent(s.actor)) seen.add(s.actor);
    if (isStageAgent(s.recipient)) seen.add(s.recipient);
  }
  for (const s of full) {
    if (isStageAgent(s.actor)) seen.add(s.actor);
    if (isStageAgent(s.recipient)) seen.add(s.recipient);
  }
  if (liveWorkState?.draftsByRole) {
    for (const id of Object.keys(liveWorkState.draftsByRole)) {
      if (isStageAgent(id)) seen.add(id);
    }
  }
  if (liveWorkState?.toolCallsByRole) {
    for (const id of Object.keys(liveWorkState.toolCallsByRole)) {
      if (isStageAgent(id)) seen.add(id);
    }
  }
  if (liveWorkState?.verdictsByRole) {
    for (const id of Object.keys(liveWorkState.verdictsByRole)) {
      if (isStageAgent(id)) seen.add(id);
    }
    if (Object.values(liveWorkState.verdictsByRole).some((v) => Array.isArray(v) && v.length > 0)) {
      seen.add('verifier');
    }
  }
  if (liveWorkState?.reviewIssues && liveWorkState.reviewIssues.length > 0) {
    seen.add('critic');
  }
  if (liveWorkState?.revisions && liveWorkState.revisions.length > 0) {
    seen.add('critic');
  }
  const order: StageAgentId[] = ['orchestrator', 'sector', 'company', 'macro', 'verifier', 'critic'];
  const agents = order.filter((id) => seen.has(id));

  const snap = {} as Record<StageAgentId, AgentSnapshot>;
  for (const id of order) {
    snap[id] = { state: 'idle', activity: 'Chờ giao việc', sinceMs: 0, stats: [], summaryLine: 'Chưa có dữ liệu' };
  }
  snap.orchestrator = {
    state: 'busy',
    activity: 'Đọc câu hỏi và lập kế hoạch phân tích',
    sinceMs: 0,
    stats: [],
    summaryLine: 'Đang đọc câu hỏi & lập kế hoạch'
  };

  const facts: Partial<Record<StageAgentId, number>> = {};
  const drafts: Partial<Record<StageAgentId, number>> = {};
  const droppedByRole: Partial<Record<StageAgentId, number>> = {};
  let checked = 0;
  let matched = 0;
  let issues = 0;
  let rounds = 0;
  let phase = 0;
  let done = false;
  let totalDropped = 0;

  const set = (id: StageAgentId, state: StageAgentState, activity: string, t: number) => {
    snap[id] = { ...snap[id], state, activity, sinceMs: t };
  };

  for (const s of steps) {
    const t = s.t_ms;
    const actor = s.actor;
    const to = s.recipient;
    phase = Math.max(phase, KIND_PHASE[s.kind] ?? phase);
    switch (s.kind) {
      case 'plan':
        set('orchestrator', 'busy', 'Giao việc cho các chuyên viên', t);
        break;
      case 'assign':
        if (isStageAgent(to)) {
          const task = readerText(String((s.detail?.task as string) || s.summary.replace(/^Giao việc:\s*/i, '')));
          set(to, 'busy', to === 'critic' ? `Kiểm tra chéo bản nháp${s.detail?.round ? ` (vòng ${s.detail.round})` : ''}` : task, t);
          if (to === 'critic') rounds = Math.max(rounds, Number(s.detail?.round) || rounds + 1);
        }
        break;
      case 'tool_result':
        if (isStageAgent(actor)) {
          facts[actor] = (facts[actor] || 0) + (asCount(s.detail?.facts) ?? 0);
          set(actor, 'busy', 'Viết nhận định từ số liệu đã tính', t);
        }
        break;
      case 'draft':
        if (isStageAgent(actor)) {
          drafts[actor] = (drafts[actor] || 0) + (asCount(s.detail?.sentences) ?? 0);
          set(actor, 'done', 'Đã gửi nhận định', t);
          set('verifier', 'busy', 'Đối chiếu số liệu trong từng câu', t);
        }
        break;
      case 'verify': {
        checked += Number(s.detail?.numbers_checked) || 0;
        matched += Number(s.detail?.numbers_matched) || 0;
        if (Array.isArray(s.detail?.verdicts)) {
          for (const v of s.detail.verdicts as Array<{ verdict?: string; role?: string }>) {
            if (v.verdict === 'dropped') {
              totalDropped += 1;
              if (v.role && isStageAgent(v.role)) {
                droppedByRole[v.role] = (droppedByRole[v.role] || 0) + 1;
              }
            }
          }
        } else if (Array.isArray(s.detail?.dropped)) {
          const dropArr = s.detail.dropped as Array<{ role?: string }>;
          totalDropped += dropArr.length;
          for (const d of dropArr) {
            if (d.role && isStageAgent(d.role)) {
              droppedByRole[d.role] = (droppedByRole[d.role] || 0) + 1;
            }
          }
        }
        set('verifier', 'done', readerText(s.summary), t);
        set('orchestrator', 'busy', 'Chờ nhận định và lắp báo cáo', t);
        break;
      }
      case 'compose':
        set('orchestrator', 'busy', 'Lắp báo cáo, gửi đi phản biện', t);
        break;
      case 'critique_issue':
        issues += 1;
        set('critic', 'done', `Gửi ${issues} yêu cầu sửa`, t);
        if (isStageAgent(to) && to !== 'critic') set(to, 'fixing', 'Sửa câu theo phản biện', t);
        break;
      case 'revision':
        if (isStageAgent(actor)) set(actor, actor === 'orchestrator' ? 'busy' : 'done', 'Đã sửa, kiểm tra lại số liệu', t);
        break;
      case 'accept':
        set('critic', 'done', readerText(s.summary), t);
        set('orchestrator', 'busy', 'Hoàn thiện báo cáo', t);
        break;
      case 'report_ready':
        done = true;
        set('orchestrator', 'done', 'Báo cáo sẵn sàng', t);
        break;
      default:
        break;
    }
  }

  // Account for live verdicts in dropped counts
  if (liveWorkState?.verdictsByRole) {
    for (const [r, list] of Object.entries(liveWorkState.verdictsByRole)) {
      if (isStageAgent(r) && Array.isArray(list)) {
        const drops = (list as Array<{ verdict?: string }>).filter((v) => v.verdict === 'dropped').length;
        if (drops > (droppedByRole[r] || 0)) {
          droppedByRole[r] = drops;
        }
      }
    }
  }

  // Stats tags
  if (facts.sector) snap.sector.stats = [`${facts.sector} số liệu`, ...(drafts.sector ? [`${drafts.sector} nhận định`] : [])];
  if (facts.company) snap.company.stats = [`${facts.company} số liệu`, ...(drafts.company ? [`${drafts.company} nhận định`] : [])];
  if (checked) snap.verifier.stats = [`${matched}/${checked} số khớp`];
  if (rounds || issues) snap.critic.stats = [`${rounds || 1} vòng`, `${issues} góp ý`];

  if (done) {
    for (const id of agents) {
      if (snap[id].state === 'busy' || snap[id].state === 'fixing') snap[id] = { ...snap[id], state: 'done' };
    }
    for (const id of planned) {
      if (isStageAgent(id) && !steps.some((s) => s.actor === id || s.recipient === id)) snap[id].state = 'unused';
    }
  }

  // Real-data generated summary line for each agent card
  const planDetail = plan?.detail || {};
  const qTypeStr = planDetail.question_type ? (QUESTION_TYPES[String(planDetail.question_type)] || String(planDetail.question_type)) : '';
  const entList = Array.isArray(planDetail.entities) ? (planDetail.entities as string[]) : [];
  const entStr = entList.length > 0 ? entList.join(', ') : '';

  if (plan) {
    snap.orchestrator.summaryLine = qTypeStr
      ? `Kế hoạch ${qTypeStr}${entStr ? `: ${entStr}` : ''}`
      : 'Kế hoạch phân tích';
  } else if (snap.orchestrator.state === 'busy') {
    snap.orchestrator.summaryLine = 'Đang lập kế hoạch phân tích';
  } else {
    snap.orchestrator.summaryLine = 'Chưa có kế hoạch';
  }

  // Specialist summary lines
  const specialistRoles: StageAgentId[] = ['company', 'sector', 'macro'];
  for (const role of specialistRoles) {
    const dCount = drafts[role] || 0;
    const dropCount = droppedByRole[role] || 0;
    if (dCount > 0) {
      snap[role].summaryLine = dropCount > 0
        ? `Viết ${dCount} nhận định, ${dropCount} bị loại`
        : `Viết ${dCount} nhận định, đều đạt`;
    } else if (facts[role]) {
      snap[role].summaryLine = `Đã tính ${facts[role]} số liệu có nguồn`;
    } else if (snap[role].state === 'busy') {
      snap[role].summaryLine = 'Đang thu thập số liệu...';
    } else if (snap[role].state === 'unused') {
      snap[role].summaryLine = 'Không dùng trong câu hỏi này';
    } else {
      snap[role].summaryLine = 'Chưa có dữ liệu';
    }
  }

  // Verifier summary line
  if (checked > 0) {
    snap.verifier.summaryLine = totalDropped > 0
      ? `Đã kiểm ${checked} số, ${matched} khớp (${totalDropped} câu bị loại)`
      : `Đã kiểm ${checked} số, ${matched} khớp (100% đạt)`;
  } else if (snap.verifier.state === 'busy') {
    snap.verifier.summaryLine = 'Đang đối chiếu số liệu...';
  } else {
    snap.verifier.summaryLine = 'Chưa có dữ liệu';
  }

  // Critic summary line
  if (issues > 0 || rounds > 0) {
    snap.critic.summaryLine = `${rounds || 1} vòng, ${issues} yêu cầu sửa`;
  } else if (snap.critic.state === 'done') {
    snap.critic.summaryLine = 'Đã duyệt, lập luận đạt chuẩn';
  } else if (snap.critic.state === 'busy') {
    snap.critic.summaryLine = 'Đang rà soát lập luận...';
  } else {
    snap.critic.summaryLine = 'Chưa có dữ liệu';
  }

  return {
    agents,
    snapshots: snap,
    phase,
    done,
    questionType: plan?.detail?.question_type as string | undefined
  };
}

export function stepEndpoints(step: TraceStep): [StageAgentId, StageAgentId] | null {
  const from = step.actor;
  const to = step.kind === 'draft' ? 'orchestrator' : step.recipient;
  if (!isStageAgent(from) || !isStageAgent(to) || from === to) return null;
  return [from, to];
}

export interface SourcedFact {
  factId: string;
  label: string;
  displayValue: string;
  sourceNoteNo?: number | null;
  sourceLocator?: string;
  source?: string;
}

export interface SentenceVerdictDetail {
  sentence: string;
  verdict: 'kept' | 'dropped';
  dropReason?: string | null;
  explanationVi?: string;
  factIds?: string[];
  role?: string;
}

export interface ToolCallDetail {
  tool: string;
  label?: string;
  arguments?: {
    entities?: string[];
    metrics?: string[];
    periods?: string[];
    [key: string]: unknown;
  };
  resultCount?: number;
  durationMs?: number;
  role?: string;
  status: 'running' | 'completed';
  facts?: SourcedFact[];
}

export interface ReviewIssueDetail {
  round?: number;
  issueType?: string;
  severity?: string;
  targetSentence?: string;
  requiredAction?: string;
  description?: string;
}

export interface SentenceRevisionDetail {
  round?: number;
  before?: string;
  after?: string;
  verified?: boolean;
}

export interface PlanSummaryDetail {
  questionType?: string;
  entities?: string[];
  metrics?: string[];
  periods?: string[];
  specialistsCalled?: string[];
  tools?: string[];
  planSummary?: string;
  rationale?: string;
  assignments?: Array<{
    agent: StageAgentId;
    agentName: string;
    task: string;
    tools?: string[];
  }>;
}

export interface VerifierStatsDetail {
  sentencesChecked: number;
  numbersChecked: number;
  numbersMatched: number;
  droppedCount: number;
}

export interface AgentWorkData {
  agentId: StageAgentId;
  draftText: string;
  isTyping: boolean;
  toolCalls: ToolCallDetail[];
  verdicts: SentenceVerdictDetail[];
  issues: ReviewIssueDetail[];
  revisions: SentenceRevisionDetail[];
  planSummary?: PlanSummaryDetail;
  facts: SourcedFact[];
  verifierStats: VerifierStatsDetail;
  criticAccepted?: string;
}

export function deriveAgentWork(
  agentId: StageAgentId,
  steps: TraceStep[],
  liveWorkState?: {
    draftsByRole: Record<string, string>;
    activeWriterRole: string | null;
    toolCallsByRole: Record<string, Array<{ tool: string; arguments?: Record<string, unknown>; resultCount?: number; durationMs?: number; role?: string; status: 'running' | 'completed' }>>;
    verdictsByRole: Record<string, Array<{ sentence: string; verdict: 'kept' | 'dropped'; dropReason?: string | null; explanationVi?: string; factIds?: string[]; role?: string }>>;
    reviewIssues: Array<{ issueType?: string; targetSentence?: string; requiredAction?: string; description?: string }>;
    revisions: Array<{ before?: string; after?: string; verified?: boolean }>;
    planSummary?: { questionType?: string; entities?: string[]; metrics?: string[]; periods?: string[]; specialistsCalled?: string[]; tools?: string[]; planSummary?: string; rationale?: string };
  }
): AgentWorkData {
  // 1. Draft text
  let draftText = liveWorkState?.draftsByRole[agentId] || '';
  if (!draftText) {
    if (agentId === 'company' || agentId === 'sector' || agentId === 'macro') {
      const draftStep = [...steps].reverse().find((s) => s.actor === agentId && s.kind === 'draft');
      if (draftStep?.detail?.draft_text && typeof draftStep.detail.draft_text === 'string') {
        draftText = draftStep.detail.draft_text;
      } else if (Array.isArray(draftStep?.detail?.sentences)) {
        draftText = (draftStep.detail.sentences as Array<{ text?: string }>)
          .map((s) => s.text || '')
          .filter(Boolean)
          .join('\n\n');
      }
    } else if (agentId === 'orchestrator') {
      const composeStep = [...steps].reverse().find((s) => s.kind === 'compose');
      if (composeStep?.detail?.draft_text && typeof composeStep.detail.draft_text === 'string') {
        draftText = composeStep.detail.draft_text;
      }
    }
  }

  // 2. Typing indicator
  const isTyping = liveWorkState?.activeWriterRole === agentId;

  // 3. Tool calls and extracted facts
  const toolCalls: ToolCallDetail[] = [];
  const extractedFacts: SourcedFact[] = [];

  const rawLiveTools = liveWorkState?.toolCallsByRole[agentId] || [];
  for (const t of rawLiveTools) {
    toolCalls.push({
      tool: t.tool,
      arguments: t.arguments as ToolCallDetail['arguments'],
      resultCount: t.resultCount,
      durationMs: t.durationMs,
      role: t.role || agentId,
      status: t.status
    });
  }

  for (const s of steps) {
    if (s.actor === agentId && s.kind === 'tool_result') {
      const stepFacts: SourcedFact[] = [];
      if (Array.isArray(s.detail?.facts)) {
        for (const f of s.detail.facts as Array<Record<string, unknown>>) {
          const sf: SourcedFact = {
            factId: String(f.fact_id || ''),
            label: String(f.label || ''),
            displayValue: String(f.display_value || f.value || ''),
            sourceNoteNo: typeof f.source_note_no === 'number' ? f.source_note_no : null,
            sourceLocator: (f.source_locator || f.source) as string | undefined
          };
          stepFacts.push(sf);
          extractedFacts.push(sf);
        }
      }

      if (toolCalls.length === 0 || !rawLiveTools.length) {
        if (Array.isArray(s.detail?.tools)) {
          for (const t of s.detail.tools as Array<{ tool?: string; arguments?: Record<string, unknown>; result_count?: number; duration_ms?: number }>) {
            toolCalls.push({
              tool: t.tool || 'query_data',
              arguments: t.arguments,
              resultCount: t.result_count,
              durationMs: t.duration_ms,
              status: 'completed',
              role: agentId,
              facts: stepFacts
            });
          }
        } else if (s.detail?.tool) {
          toolCalls.push({
            tool: String(s.detail.tool),
            label: s.detail.label as string | undefined,
            arguments: {
              label: s.detail.label as string | undefined
            },
            resultCount: Array.isArray(s.detail.facts)
              ? s.detail.facts.length
              : Array.isArray(s.detail.datasets)
                ? s.detail.datasets.length
                : undefined,
            durationMs: typeof s.detail.duration_ms === 'number' ? s.detail.duration_ms : undefined,
            status: 'completed',
            role: agentId,
            facts: stepFacts
          });
        }
      }
    }
  }

  // 4. Sentence verdicts & verifier stats
  let verdicts: SentenceVerdictDetail[] = [...(liveWorkState?.verdictsByRole[agentId] || [])];
  if (verdicts.length === 0 && agentId === 'verifier') {
    verdicts = [...(liveWorkState?.verdictsByRole.verifier || [])];
  }

  let numbersChecked = 0;
  let numbersMatched = 0;
  let sentencesChecked = 0;
  let droppedCount = 0;

  for (const s of steps) {
    if (s.kind === 'verify') {
      numbersChecked += Number(s.detail?.numbers_checked) || 0;
      numbersMatched += Number(s.detail?.numbers_matched) || 0;
      sentencesChecked += Number(s.detail?.sentences_checked) || 0;

      if (Array.isArray(s.detail?.verdicts)) {
        for (const v of s.detail.verdicts as Array<{ sentence: string; verdict: 'kept' | 'dropped'; dropReason?: string | null; explanationVi?: string; factIds?: string[]; role?: string }>) {
          if (v.verdict === 'dropped') droppedCount += 1;
          if (agentId === 'verifier' || v.role === agentId) {
            if (!verdicts.some((existing) => existing.sentence === v.sentence)) {
              verdicts.push(v);
            }
          }
        }
      }

      if (Array.isArray(s.detail?.dropped)) {
        for (const d of s.detail.dropped as Array<{ sentence?: string; text?: string; reason?: string; drop_reason?: string; explanation_vi?: string; role?: string }>) {
          droppedCount += 1;
          const sentText = d.sentence || d.text || '';
          if (agentId === 'verifier' || d.role === agentId) {
            if (sentText && !verdicts.some((existing) => existing.sentence === sentText)) {
              verdicts.push({
                sentence: sentText,
                verdict: 'dropped',
                dropReason: d.drop_reason || d.reason,
                explanationVi: d.explanation_vi || 'Số liệu không khớp dữ liệu gốc',
                role: d.role
              });
            }
          }
        }
      }
    }
  }

  // If specialist still has no verdicts, reconstruct from draft sentences
  if (verdicts.length === 0 && (agentId === 'company' || agentId === 'sector' || agentId === 'macro')) {
    const draftStep = steps.find((s) => s.actor === agentId && s.kind === 'draft');
    if (Array.isArray(draftStep?.detail?.sentences)) {
      for (const sent of draftStep.detail.sentences as Array<{ text: string; fact_ids?: string[] }>) {
        const hasFacts = sent.fact_ids && sent.fact_ids.length > 0;
        verdicts.push({
          sentence: sent.text,
          verdict: hasFacts ? 'kept' : 'dropped',
          explanationVi: hasFacts ? 'Đã đối chiếu dữ liệu gốc' : 'Chưa đủ số liệu kiểm chứng',
          factIds: sent.fact_ids || [],
          role: agentId
        });
      }
    }
  }

  // If verifier has no verdicts, construct from summary
  if (verdicts.length === 0 && agentId === 'verifier') {
    for (const s of steps) {
      if (s.kind === 'verify' && Number(s.detail?.numbers_checked) > 0) {
        verdicts.push({
          sentence: readerText(s.summary),
          verdict: 'kept',
          explanationVi: `Đã đối chiếu ${s.detail?.numbers_matched}/${s.detail?.numbers_checked} số liệu khớp dữ liệu gốc`,
          factIds: []
        });
      }
    }
  }

  // 5. Issues (criticism)
  const issues: ReviewIssueDetail[] = [];
  const rawIssues = liveWorkState?.reviewIssues || [];
  for (const iss of rawIssues) {
    issues.push({
      issueType: iss.issueType,
      targetSentence: iss.targetSentence,
      requiredAction: iss.requiredAction,
      description: iss.description
    });
  }

  for (const s of steps) {
    if (s.kind === 'critique_issue') {
      const round = typeof s.detail?.round === 'number' ? s.detail.round : 1;
      if (Array.isArray(s.detail?.issues)) {
        for (const iss of s.detail.issues as Array<{ issue_type?: string; issueType?: string; severity?: string; target_sentence?: string; targetSentence?: string; required_action?: string; requiredAction?: string; description?: string }>) {
          issues.push({
            round,
            issueType: iss.issueType || iss.issue_type,
            severity: iss.severity,
            targetSentence: iss.targetSentence || iss.target_sentence,
            requiredAction: iss.requiredAction || iss.required_action,
            description: iss.description || readerText(s.summary)
          });
        }
      } else {
        issues.push({
          round,
          issueType: (s.detail?.issue_type as string) || 'critique',
          severity: (s.detail?.severity as string) || 'MAJOR',
          targetSentence: (s.detail?.target_sentence as string) || undefined,
          requiredAction: (s.detail?.required_action as string) || 'Hiệu chỉnh câu nhận định theo yêu cầu',
          description: (s.detail?.description as string) || readerText(s.summary)
        });
      }
    }
  }

  // 6. Revisions
  const revisions: SentenceRevisionDetail[] = [];
  const rawRevs = liveWorkState?.revisions || [];
  for (const r of rawRevs) {
    revisions.push({
      before: r.before,
      after: r.after,
      verified: r.verified
    });
  }

  for (const s of steps) {
    if (s.kind === 'revision') {
      const round = typeof s.detail?.round === 'number' ? s.detail.round : 1;
      if (Array.isArray(s.detail?.revisions)) {
        for (const rev of s.detail.revisions as Array<{ before?: string; after?: string; verified?: boolean }>) {
          revisions.push({
            round,
            before: rev.before,
            after: rev.after,
            verified: rev.verified ?? true
          });
        }
      } else if (s.detail?.before && s.detail?.after) {
        revisions.push({
          round,
          before: String(s.detail.before),
          after: String(s.detail.after),
          verified: true
        });
      }
    }
  }

  // 7. Critic acceptance
  const acceptStep = steps.find((s) => s.kind === 'accept');
  const criticAccepted = acceptStep ? readerText(acceptStep.summary) : undefined;

  // 8. Plan summary and assignments (for orchestrator)
  let planSummary: PlanSummaryDetail | undefined = liveWorkState?.planSummary;
  const planStep = steps.find((s) => s.kind === 'plan');
  if (planStep) {
    const planDetail = planStep.detail || {};
    const plannedAgents = ((planDetail.agents as Array<{ agent: string; decision: string }>) || [])
      .filter((a) => a.decision === 'run')
      .map((a) => a.agent);

    const assignments: PlanSummaryDetail['assignments'] = [];
    for (const s of steps) {
      if (s.actor === 'orchestrator' && s.kind === 'assign' && isStageAgent(s.recipient)) {
        assignments.push({
          agent: s.recipient,
          agentName: STAGE_AGENTS[s.recipient].name,
          task: readerText(String(s.detail?.task || s.summary.replace(/^Giao việc:\s*/i, ''))),
          tools: Array.isArray(s.detail?.tools) ? (s.detail.tools as string[]) : undefined
        });
      }
    }

    planSummary = {
      questionType: (planDetail.question_type as string) || planSummary?.questionType,
      entities: (planDetail.entities as string[]) || planSummary?.entities,
      metrics: ((planDetail.metric_ids || planDetail.metrics) as string[]) || planSummary?.metrics,
      periods: (planDetail.periods as string[]) || planSummary?.periods,
      specialistsCalled: plannedAgents.length > 0 ? plannedAgents : planSummary?.specialistsCalled,
      tools: (planDetail.tools as string[]) || planSummary?.tools,
      planSummary: readerText(planStep.summary) || planSummary?.planSummary,
      rationale: (planDetail.rationale_vi || planDetail.rationale) as string | undefined || planSummary?.rationale,
      assignments: assignments.length > 0 ? assignments : undefined
    };
  }

  return {
    agentId,
    draftText,
    isTyping,
    toolCalls,
    verdicts,
    issues,
    revisions,
    planSummary,
    facts: extractedFacts,
    verifierStats: {
      sentencesChecked: sentencesChecked || verdicts.length,
      numbersChecked,
      numbersMatched,
      droppedCount: droppedCount || verdicts.filter((v) => v.verdict === 'dropped').length
    },
    criticAccepted
  };
}
