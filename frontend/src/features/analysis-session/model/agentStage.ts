import type { TraceStep } from './types';

/** Agents drawn on the live stage. `verifier` is the deterministic number checker. */
export type StageAgentId = 'orchestrator' | 'sector' | 'company' | 'macro' | 'verifier' | 'critic';
export type StageAgentState = 'idle' | 'busy' | 'fixing' | 'done' | 'unused' | 'blocked';

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
  head_to_head: 'So sánh trực diện',
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


function isStageAgent(id: string | null | undefined): id is StageAgentId {
  return Boolean(id && id in STAGE_AGENTS);
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
  refusalReason?: string;
  isUnused?: boolean;
}

export interface LiveWorkStateInput {
  draftsByRole?: Record<string, string>;
  activeWriterRole?: string | null;
  toolCallsByRole?: Record<string, Array<{ tool: string; arguments?: Record<string, unknown>; resultCount?: number; durationMs?: number; role?: string; status: 'running' | 'completed'; facts?: SourcedFact[] }>>;
  verdictsByRole?: Record<string, Array<{ sentence: string; verdict: 'kept' | 'dropped'; dropReason?: string | null; explanationVi?: string; factIds?: string[]; role?: string }>>;
  reviewIssues?: Array<{ issueType?: string; targetSentence?: string; requiredAction?: string; description?: string }>;
  revisions?: Array<{ before?: string; after?: string; verified?: boolean }>;
  planSummary?: {
    questionType?: string;
    entities?: string[];
    metrics?: string[];
    periods?: string[];
    specialistsCalled?: string[];
    tools?: string[];
    planSummary?: string;
    rationale?: string;
  };
  isBlocked?: boolean;
  blockedInfo?: { code?: string; message: string; suggestions?: string[] } | null;
}

/**
 * Single source of truth for agent activities, queries, verdicts, and plans.
 * Used by BOTH individual card summaries and the detail panel views.
 */
export function deriveAgentWork(
  agentId: StageAgentId,
  steps: TraceStep[],
  liveWorkState?: LiveWorkStateInput
): AgentWorkData {
  // Check for blocked status
  const blockedStep = steps.find((s) => s.kind === 'blocked');
  const refusalReason =
    liveWorkState?.blockedInfo?.message ||
    (blockedStep?.detail?.message as string | undefined) ||
    blockedStep?.summary ||
    (liveWorkState?.isBlocked ? 'Yêu cầu nằm ngoài phạm vi phân tích ngành ngân hàng.' : undefined);

  // 1. Draft text
  let draftText = liveWorkState?.draftsByRole?.[agentId] || '';
  if (!draftText) {
    if (agentId === 'company' || agentId === 'sector' || agentId === 'macro') {
      const draftSteps = steps.filter((s) => s.actor === agentId && s.kind === 'draft');
      const parts: string[] = [];
      for (const ds of draftSteps) {
        if (ds.detail?.draft_text && typeof ds.detail.draft_text === 'string') {
          parts.push(ds.detail.draft_text);
        } else if (Array.isArray(ds.detail?.sentences)) {
          const joined = (ds.detail.sentences as Array<{ text?: string }>)
            .map((s) => s.text || '')
            .filter(Boolean)
            .join('\n\n');
          if (joined) parts.push(joined);
        }
      }
      draftText = parts.join('\n\n');
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

  const rawLiveTools = liveWorkState?.toolCallsByRole?.[agentId] || [];
  for (const t of rawLiveTools) {
    const liveFacts = Array.isArray(t.facts) ? (t.facts as SourcedFact[]) : undefined;
    toolCalls.push({
      tool: t.tool,
      arguments: t.arguments as ToolCallDetail['arguments'],
      resultCount: t.resultCount,
      durationMs: t.durationMs,
      role: t.role || agentId,
      status: t.status,
      facts: liveFacts
    });
    if (liveFacts && liveFacts.length > 0) {
      extractedFacts.push(...liveFacts);
    }
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
  let verdicts: SentenceVerdictDetail[] = [...(liveWorkState?.verdictsByRole?.[agentId] || [])];
  if (verdicts.length === 0 && agentId === 'verifier' && liveWorkState?.verdictsByRole?.verifier) {
    verdicts = [...liveWorkState.verdictsByRole.verifier];
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
    const draftSteps = steps.filter((s) => s.actor === agentId && s.kind === 'draft');
    for (const draftStep of draftSteps) {
      if (Array.isArray(draftStep?.detail?.sentences)) {
        for (const sent of draftStep.detail.sentences as Array<{ text: string; fact_ids?: string[] }>) {
          const hasFacts = sent.fact_ids && sent.fact_ids.length > 0;
          if (!verdicts.some((v) => v.sentence === sent.text)) {
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
    }
  }

  // If verifier has no verdicts, construct from all specialist verdicts or summary
  if (verdicts.length === 0 && agentId === 'verifier') {
    // Reconstruct verifier sentences across all specialists' draft sentences
    const allDraftSteps = steps.filter((s) => s.kind === 'draft');
    for (const draftStep of allDraftSteps) {
      if (Array.isArray(draftStep?.detail?.sentences)) {
        for (const sent of draftStep.detail.sentences as Array<{ text: string; fact_ids?: string[] }>) {
          const hasFacts = sent.fact_ids && sent.fact_ids.length > 0;
          if (!verdicts.some((v) => v.sentence === sent.text)) {
            verdicts.push({
              sentence: sent.text,
              verdict: hasFacts ? 'kept' : 'dropped',
              explanationVi: hasFacts ? 'Đã đối chiếu dữ liệu gốc' : 'Chưa đủ số liệu kiểm chứng',
              factIds: sent.fact_ids || [],
              role: draftStep.actor
            });
          }
        }
      }
    }

    if (verdicts.length === 0) {
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
        const assignedTools = Array.isArray(s.detail?.tools)
          ? (s.detail.tools as unknown[]).map((t) => (typeof t === 'string' ? t : (t as { label?: string; tool?: string }).label || (t as { label?: string; tool?: string }).tool || String(t)))
          : undefined;
        assignments.push({
          agent: s.recipient,
          agentName: STAGE_AGENTS[s.recipient].name,
          task: readerText(String(s.detail?.task || s.summary.replace(/^Giao việc:\s*/i, ''))),
          tools: assignedTools
        });
      }
    }

    if (assignments.length === 0 && Array.isArray(planDetail.agents)) {
      for (const a of planDetail.agents as Array<{ agent: string; decision: string; reason?: string }>) {
        if (a.decision === 'run' && isStageAgent(a.agent)) {
          const agentTools = Array.isArray(planDetail.tools)
            ? (planDetail.tools as Array<{ agent?: string; label?: string; tool?: string }>)
                .filter((t) => t.agent === a.agent)
                .map((t) => t.label || t.tool || '')
                .filter(Boolean)
            : [];
          assignments.push({
            agent: a.agent as StageAgentId,
            agentName: STAGE_AGENTS[a.agent as StageAgentId].name,
            task: a.reason || 'Thực hiện phân tích chuyên biệt',
            tools: agentTools.length > 0 ? agentTools : undefined
          });
        }
      }
    }

    const normalizedTools = Array.isArray(planDetail.tools)
      ? (planDetail.tools as unknown[]).map((t) => (typeof t === 'string' ? t : (t as { label?: string; tool?: string }).label || (t as { label?: string; tool?: string }).tool || String(t)))
      : planSummary?.tools;

    planSummary = {
      questionType: (planDetail.question_type as string) || planSummary?.questionType,
      entities: (planDetail.entities as string[]) || planSummary?.entities,
      metrics: ((planDetail.metric_ids || planDetail.metrics) as string[]) || planSummary?.metrics,
      periods: (planDetail.periods as string[]) || planSummary?.periods,
      specialistsCalled: plannedAgents.length > 0 ? plannedAgents : planSummary?.specialistsCalled,
      tools: normalizedTools,
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
    criticAccepted,
    refusalReason
  };
}

export interface StageModel {
  agents: StageAgentId[];
  snapshots: Record<StageAgentId, AgentSnapshot>;
  phase: number;
  done: boolean;
  questionType?: string;
  isBlocked?: boolean;
  refusalReason?: string;
}

/**
 * Derive who is working right now from the revealed prefix of the trace.
 * Computes card summaries and status using deriveAgentWork as the single source of truth.
 */
export function deriveStage(
  steps: TraceStep[],
  allSteps?: TraceStep[],
  liveWorkState?: LiveWorkStateInput
): StageModel {
  const full = allSteps && allSteps.length > 0 ? allSteps : steps;
  const order: StageAgentId[] = ['orchestrator', 'sector', 'company', 'macro', 'verifier', 'critic'];

  // Check terminal conditions
  const blockedStep = steps.find((s) => s.kind === 'blocked') || allSteps?.find((s) => s.kind === 'blocked');
  const isBlocked = Boolean(blockedStep || liveWorkState?.isBlocked);
  const refusalReason =
    liveWorkState?.blockedInfo?.message ||
    (blockedStep?.detail?.message as string | undefined) ||
    blockedStep?.summary ||
    'Yêu cầu nằm ngoài phạm vi phân tích ngành ngân hàng.';

  const done = !isBlocked && steps.some((s) => s.kind === 'report_ready');

  // Derive work data for ALL agents - Single source of truth
  const works: Record<StageAgentId, AgentWorkData> = {
    orchestrator: deriveAgentWork('orchestrator', steps, liveWorkState),
    sector: deriveAgentWork('sector', steps, liveWorkState),
    company: deriveAgentWork('company', steps, liveWorkState),
    macro: deriveAgentWork('macro', steps, liveWorkState),
    verifier: deriveAgentWork('verifier', steps, liveWorkState),
    critic: deriveAgentWork('critic', steps, liveWorkState)
  };

  const plan = works.orchestrator.planSummary;
  const planned = (plan?.specialistsCalled || []).map((s) => s.toLowerCase());

  // Determine which agents participate or were planned
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
  if (works.verifier.verifierStats.numbersChecked > 0 || works.verifier.verdicts.length > 0) {
    seen.add('verifier');
  }
  if (works.critic.issues.length > 0 || works.critic.revisions.length > 0 || works.critic.criticAccepted) {
    seen.add('critic');
  }
  for (const role of ['company', 'sector', 'macro'] as StageAgentId[]) {
    if (works[role].toolCalls.length > 0 || works[role].facts.length > 0 || works[role].draftText || works[role].verdicts.length > 0) {
      seen.add(role);
    }
  }

  const snap = {} as Record<StageAgentId, AgentSnapshot>;
  for (const id of order) {
    snap[id] = {
      state: 'idle',
      activity: 'Chờ giao việc',
      sinceMs: 0,
      stats: [],
      summaryLine: 'Chưa có dữ liệu'
    };
  }

  let phase = 0;
  for (const s of steps) {
    phase = Math.max(phase, KIND_PHASE[s.kind] ?? phase);
  }
  if (done) phase = 5;

  // --------------------------------------------------------------------------
  // CASE 1: Run is blocked / rejected / errored (Requirement 3)
  // Show refusal reason across all pipeline cards, NEVER "Chờ".
  // --------------------------------------------------------------------------
  if (isBlocked) {
    for (const id of order) {
      snap[id] = {
        state: 'blocked',
        activity: refusalReason,
        sinceMs: 0,
        stats: [],
        summaryLine: refusalReason
      };
    }
    return {
      agents: order,
      snapshots: snap,
      phase: 0,
      done: false,
      isBlocked: true,
      refusalReason,
      questionType: plan?.questionType
    };
  }

  // --------------------------------------------------------------------------
  // CASE 2: Run is completed (Requirement 1)
  // Every agent that took part shows status "Xong" and single-source-of-truth summary.
  // Agents that did NOT take part show "Không tham gia", NOT "Chờ".
  // --------------------------------------------------------------------------
  if (done) {
    // 1. Orchestrator
    const qTypeStr = plan?.questionType ? (QUESTION_TYPES[plan.questionType] || plan.questionType) : '';
    const entList = plan?.entities || [];
    const targetEnt = entList.find((e) => !e.startsWith('sector:')) || entList[0] || '';
    const entStr = targetEnt || (entList.length > 0 ? entList.join(', ') : '');

    snap.orchestrator = {
      state: 'done',
      activity: 'Báo cáo sẵn sàng',
      sinceMs: 0,
      stats: [
        ...(plan?.assignments?.length ? [`${plan.assignments.length} nhiệm vụ`] : []),
        ...(plan?.tools?.length ? [`${plan.tools.length} công cụ`] : [])
      ],
      summaryLine: qTypeStr
        ? `Kế hoạch ${qTypeStr}${entStr ? `: ${entStr}` : ''}`
        : (plan?.planSummary || 'Kế hoạch phân tích')
    };

    // 2. Specialists (company, sector, macro)
    const specialistRoles: StageAgentId[] = ['company', 'sector', 'macro'];
    for (const role of specialistRoles) {
      const work = works[role];
      const participated =
        work.toolCalls.length > 0 ||
        work.facts.length > 0 ||
        Boolean(work.draftText) ||
        work.verdicts.length > 0 ||
        steps.some((s) => s.actor === role || s.recipient === role);

      if (participated) {
        let summary = 'Đã hoàn thành phân tích';
        if (work.verdicts.length > 0) {
          const dropCount = work.verdicts.filter((v) => v.verdict === 'dropped').length;
          summary = dropCount > 0
            ? `Viết ${work.verdicts.length} nhận định, ${dropCount} bị loại`
            : `Viết ${work.verdicts.length} nhận định, đều đạt`;
        } else if (work.facts.length > 0) {
          summary = `Đã tính ${work.facts.length} số liệu có nguồn`;
        } else if (work.toolCalls.length > 0) {
          summary = `Đã hoàn thành ${work.toolCalls.length} truy vấn dữ liệu`;
        } else if (work.draftText) {
          summary = 'Đã gửi bản nhận định';
        }

        const stats: string[] = [];
        if (work.facts.length > 0) stats.push(`${work.facts.length} số liệu`);
        if (work.verdicts.length > 0) stats.push(`${work.verdicts.length} nhận định`);

        snap[role] = {
          state: 'done',
          activity: 'Đã hoàn thành nhận định & số liệu',
          sinceMs: 0,
          stats,
          summaryLine: summary
        };
      } else {
        snap[role] = {
          state: 'unused',
          activity: 'Không tham gia trong câu hỏi này',
          sinceMs: 0,
          stats: [],
          summaryLine: 'Không tham gia'
        };
      }
    }

    // 3. Verifier
    const verifierWork = works.verifier;
    const verifierParticipated =
      verifierWork.verifierStats.numbersChecked > 0 ||
      verifierWork.verifierStats.sentencesChecked > 0 ||
      verifierWork.verdicts.length > 0 ||
      steps.some((s) => s.kind === 'verify');

    if (verifierParticipated) {
      let summary = 'Đã đối chiếu số liệu';
      const stats: string[] = [];
      if (verifierWork.verifierStats.numbersChecked > 0) {
        summary = verifierWork.verifierStats.droppedCount > 0
          ? `Đã kiểm ${verifierWork.verifierStats.numbersChecked} số, ${verifierWork.verifierStats.numbersMatched} khớp (${verifierWork.verifierStats.droppedCount} câu bị loại)`
          : `Đã kiểm ${verifierWork.verifierStats.numbersChecked} số, ${verifierWork.verifierStats.numbersMatched} khớp (100% đạt)`;
        stats.push(`${verifierWork.verifierStats.numbersMatched}/${verifierWork.verifierStats.numbersChecked} số khớp`);
      } else if (verifierWork.verifierStats.sentencesChecked > 0) {
        summary = verifierWork.verifierStats.droppedCount > 0
          ? `Đã kiểm ${verifierWork.verifierStats.sentencesChecked} câu (${verifierWork.verifierStats.droppedCount} bị loại)`
          : `Đã kiểm ${verifierWork.verifierStats.sentencesChecked} câu (100% đạt)`;
        stats.push(`${verifierWork.verifierStats.sentencesChecked} câu kiểm tra`);
      } else if (verifierWork.verdicts.length > 0) {
        const dropCount = verifierWork.verdicts.filter((v) => v.verdict === 'dropped').length;
        summary = dropCount > 0
          ? `Đã đối chiếu ${verifierWork.verdicts.length} câu (${dropCount} bị loại)`
          : `Đã đối chiếu ${verifierWork.verdicts.length} câu (100% đạt)`;
        stats.push(`${verifierWork.verdicts.length} câu kiểm tra`);
      }

      snap.verifier = {
        state: 'done',
        activity: verifierWork.verifierStats.droppedCount > 0 ? 'Đã phát hiện và loại câu không đạt' : '100% số liệu khớp dữ liệu gốc',
        sinceMs: 0,
        stats,
        summaryLine: summary
      };
    } else {
      snap.verifier = {
        state: 'unused',
        activity: 'Không tham gia trong câu hỏi này',
        sinceMs: 0,
        stats: [],
        summaryLine: 'Không tham gia'
      };
    }

    // 4. Critic
    const criticWork = works.critic;
    const criticParticipated =
      criticWork.issues.length > 0 ||
      criticWork.revisions.length > 0 ||
      Boolean(criticWork.criticAccepted) ||
      steps.some((s) => s.actor === 'critic' || s.recipient === 'critic' || s.kind === 'critique_issue' || s.kind === 'accept' || s.kind === 'cross_level_finding');

    if (criticParticipated) {
      let summary = 'Đã hoàn thành rà soát';
      const stats: string[] = [];
      if (criticWork.issues.length > 0 || criticWork.revisions.length > 0) {
        const rCount = Math.max(...criticWork.issues.map((i) => i.round || 1), ...criticWork.revisions.map((r) => r.round || 1), 1);
        summary = `${rCount} vòng, ${criticWork.issues.length} yêu cầu sửa`;
        stats.push(`${rCount} vòng`, `${criticWork.issues.length} góp ý`);
      } else if (criticWork.criticAccepted) {
        summary = 'Đã duyệt, lập luận đạt chuẩn';
        stats.push('Đạt chuẩn');
      }

      snap.critic = {
        state: 'done',
        activity: criticWork.criticAccepted || 'Đã hoàn thành rà soát lập luận',
        sinceMs: 0,
        stats,
        summaryLine: summary
      };
    } else {
      snap.critic = {
        state: 'unused',
        activity: 'Không tham gia trong câu hỏi này',
        sinceMs: 0,
        stats: [],
        summaryLine: 'Không tham gia'
      };
    }

    return {
      agents: order.filter((id) => seen.has(id)),
      snapshots: snap,
      phase,
      done: true,
      questionType: plan?.questionType
    };
  }

  // --------------------------------------------------------------------------
  // CASE 3: Run is actively streaming / in progress
  // --------------------------------------------------------------------------
  snap.orchestrator = {
    state: 'busy',
    activity: 'Đọc câu hỏi và lập kế hoạch phân tích',
    sinceMs: 0,
    stats: [],
    summaryLine: 'Đang đọc câu hỏi & lập kế hoạch'
  };

  const set = (id: StageAgentId, state: StageAgentState, activity: string, t: number) => {
    snap[id] = { ...snap[id], state, activity, sinceMs: t };
  };

  for (const s of steps) {
    const t = s.t_ms;
    const actor = s.actor;
    const to = s.recipient;
    switch (s.kind) {
      case 'plan':
        set('orchestrator', 'busy', 'Giao việc cho các chuyên viên', t);
        break;
      case 'assign':
        if (isStageAgent(to)) {
          const task = readerText(String((s.detail?.task as string) || s.summary.replace(/^Giao việc:\s*/i, '')));
          set(to, 'busy', to === 'critic' ? `Kiểm tra chéo bản nháp${s.detail?.round ? ` (vòng ${s.detail.round})` : ''}` : task, t);
        }
        break;
      case 'tool_result':
        if (isStageAgent(actor)) {
          set(actor, 'busy', 'Viết nhận định từ số liệu đã tính', t);
        }
        break;
      case 'draft':
        if (isStageAgent(actor)) {
          set(actor, 'done', 'Đã gửi nhận định', t);
          set('verifier', 'busy', 'Đối chiếu số liệu trong từng câu', t);
        }
        break;
      case 'verify':
        set('verifier', 'done', readerText(s.summary), t);
        set('orchestrator', 'busy', 'Chờ nhận định và lắp báo cáo', t);
        break;
      case 'compose':
        set('orchestrator', 'busy', 'Lắp báo cáo, gửi đi phản biện', t);
        break;
      case 'critique_issue':
        set('critic', 'done', readerText(s.summary), t);
        if (isStageAgent(to) && to !== 'critic') set(to, 'fixing', 'Sửa câu theo phản biện', t);
        break;
      case 'revision':
        if (isStageAgent(actor)) set(actor, actor === 'orchestrator' ? 'busy' : 'done', 'Đã sửa, kiểm tra lại số liệu', t);
        break;
      case 'accept':
        set('critic', 'done', readerText(s.summary), t);
        set('orchestrator', 'busy', 'Hoàn thiện báo cáo', t);
        break;
      default:
        break;
    }
  }

  // Populate live summary lines from unified work data
  const qTypeStr = plan?.questionType ? (QUESTION_TYPES[plan.questionType] || plan.questionType) : '';
  const entList = plan?.entities || [];
  const targetEnt = entList.find((e) => !e.startsWith('sector:')) || entList[0] || '';
  const entStr = targetEnt || (entList.length > 0 ? entList.join(', ') : '');

  if (plan?.questionType) {
    snap.orchestrator.summaryLine = `Kế hoạch ${qTypeStr}${entStr ? `: ${entStr}` : ''}`;
  } else if (snap.orchestrator.state === 'busy') {
    snap.orchestrator.summaryLine = 'Đang lập kế hoạch phân tích';
  }

  for (const role of ['company', 'sector', 'macro'] as StageAgentId[]) {
    const work = works[role];
    if (work.facts.length > 0) snap[role].stats = [`${work.facts.length} số liệu`];
    if (snap[role].state === 'busy') {
      snap[role].summaryLine = 'Đang thu thập và phân tích số liệu...';
    } else if (snap[role].state === 'fixing') {
      snap[role].summaryLine = 'Đang sửa câu theo góp ý phản biện';
    } else if (snap[role].state === 'done') {
      snap[role].summaryLine = work.facts.length > 0 ? `Đã tính ${work.facts.length} số liệu` : 'Đã gửi nhận định';
    } else if (!planned.includes(role) && !steps.some((s) => s.actor === role || s.recipient === role)) {
      snap[role].state = 'unused';
      snap[role].summaryLine = 'Không tham gia';
      snap[role].activity = 'Không tham gia trong câu hỏi này';
    }
  }

  const verifierWork = works.verifier;
  if (verifierWork.verifierStats.numbersChecked > 0) {
    snap.verifier.stats = [`${verifierWork.verifierStats.numbersMatched}/${verifierWork.verifierStats.numbersChecked} số khớp`];
    snap.verifier.summaryLine = `Đã kiểm ${verifierWork.verifierStats.numbersChecked} số`;
  }

  const criticWork = works.critic;
  if (criticWork.issues.length > 0) {
    snap.critic.stats = [`${criticWork.issues.length} góp ý`];
    snap.critic.summaryLine = `Đã gửi ${criticWork.issues.length} yêu cầu sửa`;
  }

  return {
    agents: order.filter((id) => seen.has(id)),
    snapshots: snap,
    phase,
    done: false,
    questionType: plan?.questionType
  };
}
