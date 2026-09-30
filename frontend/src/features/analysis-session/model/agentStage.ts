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
export function deriveStage(steps: TraceStep[]): StageModel {
  const plan = steps.find((s) => s.kind === 'plan');
  const planned = ((plan?.detail?.agents as Array<{ agent: string; decision: string }> | undefined) || [])
    .filter((a) => a.decision === 'run')
    .map((a) => a.agent.toLowerCase());

  const seen = new Set<StageAgentId>(['orchestrator']);
  for (const id of planned) if (isStageAgent(id)) seen.add(id);
  for (const s of steps) {
    if (isStageAgent(s.actor)) seen.add(s.actor);
    if (isStageAgent(s.recipient)) seen.add(s.recipient);
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
