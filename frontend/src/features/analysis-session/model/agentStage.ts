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
}

export const PHASES = ['Lập kế hoạch', 'Thu thập số liệu', 'Viết nhận định', 'Kiểm tra số liệu', 'Phản biện', 'Hoàn tất'] as const;

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
  }
): StageModel {
  const full = allSteps && allSteps.length > 0 ? allSteps : steps;
  const plan = full.find((s) => s.kind === 'plan') || steps.find((s) => s.kind === 'plan');
  const planned = ((plan?.detail?.agents as Array<{ agent: string; decision: string }> | undefined) || [])
    .filter((a) => a.decision === 'run')
    .map((a) => a.agent.toLowerCase());

  const seen = new Set<StageAgentId>(['orchestrator']);
  for (const id of planned) if (isStageAgent(id)) seen.add(id);
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
  const order: StageAgentId[] = ['orchestrator', 'sector', 'company', 'macro', 'verifier', 'critic'];
  const agents = order.filter((id) => seen.has(id));

  const snap = {} as Record<StageAgentId, AgentSnapshot>;
  for (const id of order) snap[id] = { state: 'idle', activity: 'Chờ giao việc', sinceMs: 0, stats: [] };
  snap.orchestrator = { state: 'busy', activity: 'Đọc câu hỏi và lập kế hoạch phân tích', sinceMs: 0, stats: [] };

  const facts: Partial<Record<StageAgentId, number>> = {};
  const drafts: Partial<Record<StageAgentId, number>> = {};
  let checked = 0;
  let matched = 0;
  let issues = 0;
  let rounds = 0;
  let phase = 0;
  let done = false;

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
      case 'verify':
        checked += Number(s.detail?.numbers_checked) || 0;
        matched += Number(s.detail?.numbers_matched) || 0;
        set('verifier', 'done', readerText(s.summary), t);
        set('orchestrator', 'busy', 'Chờ nhận định và lắp báo cáo', t);
        break;
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

export interface AgentWorkData {
  agentId: StageAgentId;
  draftText: string;
  isTyping: boolean;
  toolCalls: Array<{
    tool: string;
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
  }>;
  verdicts: Array<{
    sentence: string;
    verdict: 'kept' | 'dropped';
    dropReason?: string | null;
    explanationVi?: string;
    factIds?: string[];
    role?: string;
  }>;
  issues: Array<{
    issueType?: string;
    targetSentence?: string;
    requiredAction?: string;
    description?: string;
  }>;
  revisions: Array<{
    before?: string;
    after?: string;
    verified?: boolean;
  }>;
  planSummary?: {
    questionType?: string;
    entities?: string[];
    metrics?: string[];
    periods?: string[];
    specialistsCalled?: string[];
    tools?: string[];
    planSummary?: string;
  };
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
    planSummary?: { questionType?: string; entities?: string[]; metrics?: string[]; periods?: string[]; specialistsCalled?: string[]; tools?: string[]; planSummary?: string };
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

  // 3. Tool calls
  const toolCalls = [...(liveWorkState?.toolCallsByRole[agentId] || [])];
  if (toolCalls.length === 0) {
    for (const s of steps) {
      if (s.actor === agentId && s.kind === 'tool_result') {
        if (Array.isArray(s.detail?.tools)) {
          for (const t of s.detail.tools as Array<{ tool?: string; arguments?: Record<string, unknown>; result_count?: number; duration_ms?: number }>) {
            toolCalls.push({
              tool: t.tool || 'query_data',
              arguments: t.arguments,
              resultCount: t.result_count,
              durationMs: t.duration_ms,
              status: 'completed',
              role: agentId
            });
          }
        } else if (s.detail?.tool) {
          toolCalls.push({
            tool: String(s.detail.tool),
            arguments: {
              label: s.detail.label as string | undefined
            },
            resultCount: Array.isArray(s.detail.facts)
              ? s.detail.facts.length
              : Array.isArray(s.detail.datasets)
                ? s.detail.datasets.length
                : undefined,
            status: 'completed',
            role: agentId
          });
        }
      }
    }
  }

  // 4. Sentence verdicts
  let verdicts = [...(liveWorkState?.verdictsByRole[agentId] || [])];
  if (verdicts.length === 0 && agentId === 'verifier') {
    verdicts = [...(liveWorkState?.verdictsByRole.verifier || [])];
  }
  if (verdicts.length === 0) {
    if (agentId === 'verifier') {
      for (const s of steps) {
        if (s.kind === 'verify') {
          if (Array.isArray(s.detail?.verdicts)) {
            verdicts.push(
              ...(s.detail.verdicts as Array<{
                sentence: string;
                verdict: 'kept' | 'dropped';
                dropReason?: string | null;
                explanationVi?: string;
                factIds?: string[];
              }>)
            );
          } else if (Number(s.detail?.numbers_checked) > 0) {
            verdicts.push({
              sentence: readerText(s.summary),
              verdict: 'kept',
              explanationVi: `Đã đối chiếu ${s.detail.numbers_matched}/${s.detail.numbers_checked} số liệu khớp dữ liệu gốc`,
              factIds: []
            });
          }
        }
      }
    } else {
      // Check if any verify step has verdicts for this agent's sentences
      const agentDraft = steps.find((s) => s.actor === agentId && s.kind === 'draft');
      if (Array.isArray(agentDraft?.detail?.sentences)) {
        for (const sent of agentDraft.detail.sentences as Array<{ text: string; fact_ids?: string[] }>) {
          verdicts.push({
            sentence: sent.text,
            verdict: sent.fact_ids && sent.fact_ids.length > 0 ? 'kept' : 'dropped',
            explanationVi:
              sent.fact_ids && sent.fact_ids.length > 0
                ? 'Đã đối chiếu dữ liệu gốc'
                : 'Chưa đủ số liệu kiểm chứng',
            factIds: sent.fact_ids || []
          });
        }
      }
    }
  }

  // 5. Issues (criticism)
  const issues = [...(liveWorkState?.reviewIssues || [])];
  if (issues.length === 0) {
    for (const s of steps) {
      if (s.kind === 'critique_issue') {
        if (Array.isArray(s.detail?.issues)) {
          issues.push(...(s.detail.issues as Array<{ issueType?: string; targetSentence?: string; requiredAction?: string; description?: string }>));
        } else {
          issues.push({
            issueType: 'critique',
            description: readerText(s.summary),
            requiredAction: 'Hiệu chỉnh câu nhận định theo yêu cầu'
          });
        }
      }
    }
  }

  // 6. Revisions
  const revisions = [...(liveWorkState?.revisions || [])];
  if (revisions.length === 0) {
    for (const s of steps) {
      if (s.kind === 'revision') {
        if (Array.isArray(s.detail?.revisions)) {
          revisions.push(...(s.detail.revisions as Array<{ before?: string; after?: string; verified?: boolean }>));
        } else if (s.detail?.before && s.detail?.after) {
          revisions.push({
            before: String(s.detail.before),
            after: String(s.detail.after),
            verified: true
          });
        }
      }
    }
  }

  // 7. Plan summary (especially for orchestrator)
  let planSummary = liveWorkState?.planSummary;
  if (!planSummary) {
    const planStep = steps.find((s) => s.kind === 'plan');
    if (planStep) {
      const planDetail = planStep.detail || {};
      const plannedAgents = (
        (planDetail.agents as Array<{ agent: string; decision: string }>) || []
      )
        .filter((a) => a.decision === 'run')
        .map((a) => a.agent);

      planSummary = {
        questionType: (planDetail.question_type as string) || undefined,
        entities: (planDetail.entities as string[]) || undefined,
        metrics: ((planDetail.metric_ids || planDetail.metrics) as string[]) || undefined,
        periods: (planDetail.periods as string[]) || undefined,
        specialistsCalled: plannedAgents.length > 0 ? plannedAgents : undefined,
        planSummary: readerText(planStep.summary)
      };
    }
  }

  return {
    agentId,
    draftText,
    isTyping,
    toolCalls,
    verdicts,
    issues,
    revisions,
    planSummary
  };
}
