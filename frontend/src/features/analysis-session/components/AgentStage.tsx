import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowRight,
  BookOpenCheck,
  Building2,
  Check,
  ChevronDown,
  FileText,
  Landmark,
  Network,
  PencilLine,
  RefreshCw,
  Scale,
  ShieldCheck,
  Sigma
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { TraceStep } from '../model/types';
import type { LiveWorkState } from '../useTraceStream';
import {
  PHASES,
  STAGE_AGENTS,
  QUESTION_TYPES,
  deriveStage,
  deriveAgentWork,
  readerText,
  stepEndpoints,
  type AgentWorkData,
  type StageAgentId,
  type StageAgentState,
  type LiveWorkStateInput
} from '../model/agentStage';

export interface AgentStageProps {
  steps: TraceStep[];
  query?: string;
  live?: boolean;
  reportId?: string | null;
  isDisconnected?: boolean;
  liveWorkState?: LiveWorkState | LiveWorkStateInput;
  onOpenReport?: (reportId: string) => void;
  onRetry?: () => void;
  autoRedirect?: boolean;
}

const ICONS: Record<StageAgentId, LucideIcon> = {
  orchestrator: Network,
  sector: Landmark,
  company: Building2,
  macro: Scale,
  verifier: Sigma,
  critic: ShieldCheck
};

const STATE_LABEL: Record<StageAgentState, string> = {
  idle: 'Chờ',
  busy: 'Đang làm',
  fixing: 'Đang sửa',
  done: 'Xong',
  unused: 'Không tham gia',
  blocked: 'Từ chối'
};

function clock(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

/** No staged reveal when the user asks for reduced motion (or the environment cannot tell). */
function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return true;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function packetLabel(step: TraceStep): string {
  switch (step.kind) {
    case 'assign':
      return 'Giao việc';
    case 'tool_result':
      return 'Số liệu';
    case 'draft':
      return 'Nhận định';
    case 'verify':
      return 'Kết quả kiểm tra';
    case 'compose':
      return 'Bản nháp';
    case 'critique_issue':
      return 'Yêu cầu sửa';
    case 'revision':
      return 'Bản sửa';
    case 'accept':
      return 'Duyệt';
    default:
      return '';
  }
}

function who(id: string | null | undefined): string {
  if (!id) return '';
  return id in STAGE_AGENTS ? STAGE_AGENTS[id as StageAgentId].name : id === 'system' ? 'Hệ thống' : id;
}

export const AgentStage: React.FC<AgentStageProps> = ({
  steps,
  query,
  live = true,
  reportId,
  isDisconnected = false,
  liveWorkState,
  onOpenReport,
  onRetry,
  autoRedirect = true
}) => {
  // Steps often arrive in bursts; reveal them one by one so every hand-off is visible.
  const isTerminal = steps.some((s) => s.kind === 'blocked' || s.kind === 'report_ready') || Boolean(liveWorkState?.isBlocked);
  const [shown, setShown] = useState(() => (live && !isTerminal ? 0 : steps.length));
  useEffect(() => {
    if (shown >= steps.length) return;
    const delay = prefersReducedMotion() || !live || isTerminal ? 0 : shown === 0 ? 120 : 700;
    const t = setTimeout(() => setShown((n) => Math.min(n + 1, steps.length)), delay);
    return () => clearTimeout(t);
  }, [shown, steps.length, live, isTerminal]);

  const visible = useMemo(() => steps.slice(0, shown), [steps, shown]);
  const model = useMemo(() => deriveStage(visible, steps, liveWorkState), [visible, steps, liveWorkState]);
  const last = visible[visible.length - 1];

  // Local seconds counter while the run is live, so waiting on a model still reads as work in progress.
  const [tickMs, setTickMs] = useState(0);
  useEffect(() => {
    if (!live || model.done || isDisconnected) return;
    const id = setInterval(() => setTickMs((t) => t + 1000), 1000);
    return () => clearInterval(id);
  }, [live, model.done, isDisconnected]);

  const [prevStepsLength, setPrevStepsLength] = useState(steps.length);
  if (steps.length === 0 && prevStepsLength !== 0) {
    setPrevStepsLength(0);
    setTickMs(0);
  } else if (steps.length !== prevStepsLength) {
    setPrevStepsLength(steps.length);
  }

  const elapsed =
    model.done || (!live && !isDisconnected)
      ? last?.t_ms ?? 0
      : Math.max(last?.t_ms ?? 0, tickMs);

  const effectiveReportId =
    reportId || (steps.find((s) => s.kind === 'report_ready')?.detail?.report_id as string | undefined) || null;
  const isBlocked = steps.some((s) => s.kind === 'blocked') || Boolean(liveWorkState?.isBlocked) || Boolean(model.isBlocked);
  const ready = model.done && Boolean(effectiveReportId) && !isBlocked;
  const [stay, setStay] = useState(false);

  useEffect(() => {
    if (!ready || !effectiveReportId || stay || !onOpenReport || !live || autoRedirect === false) return;
    const t = setTimeout(() => onOpenReport(effectiveReportId), prefersReducedMotion() ? 0 : 1800);
    return () => clearTimeout(t);
  }, [ready, effectiveReportId, stay, onOpenReport, live, autoRedirect]);

  // Active agent currently running in the multi-agent pipeline
  const currentlyRunningAgent: StageAgentId = useMemo(() => {
    if (liveWorkState?.activeWriterRole && model.agents.includes(liveWorkState.activeWriterRole as StageAgentId)) {
      return liveWorkState.activeWriterRole as StageAgentId;
    }
    const working = model.agents.find(
      (a) => model.snapshots[a].state === 'busy' || model.snapshots[a].state === 'fixing'
    );
    if (working) return working;

    const specialist = model.agents.find(
      (a) => (a === 'company' || a === 'sector') && model.snapshots[a].state === 'done'
    );
    if (specialist) return specialist;

    return model.agents[0] || 'orchestrator';
  }, [liveWorkState?.activeWriterRole, model.agents, model.snapshots]);

  // Selected agent for inspection; if user selected an agent manually, stick to their choice
  const [selectedAgentId, setSelectedAgentId] = useState<StageAgentId | null>(null);

  const activeAgentId: StageAgentId = useMemo(() => {
    if (selectedAgentId && model.agents.includes(selectedAgentId)) {
      return selectedAgentId;
    }
    return currentlyRunningAgent;
  }, [selectedAgentId, currentlyRunningAgent, model.agents]);

  const runningAgentHint =
    selectedAgentId &&
    selectedAgentId !== currentlyRunningAgent &&
    live &&
    !model.done &&
    !isBlocked &&
    !isDisconnected
      ? currentlyRunningAgent
      : null;

  const currentWork = useMemo(
    () => deriveAgentWork(activeAgentId, visible, liveWorkState),
    [activeAgentId, visible, liveWorkState]
  );

  const lastEnds = last ? stepEndpoints(last) : null;

  return (
    <section className="overflow-hidden rounded-2xl border border-border-subtle bg-surface-primary shadow-[0_1px_2px_rgba(29,28,26,0.04),0_20px_44px_-28px_rgba(60,45,20,0.35)]">
      <header className="border-b border-border-subtle px-5 pt-5 pb-4 sm:px-7">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="m-0 flex flex-wrap items-center gap-2 text-[13px] text-text-secondary">
              <span
                className={`size-2 rounded-full ${
                  isDisconnected
                    ? 'bg-warning'
                    : isBlocked
                    ? 'bg-danger'
                    : model.done
                    ? 'bg-success'
                    : 'bg-amber agent-live-dot'
                }`}
                aria-hidden="true"
              />
              <span className="font-medium text-text-primary">
                {isDisconnected
                  ? 'Mất kết nối'
                  : isBlocked
                  ? 'Yêu cầu bị từ chối'
                  : model.done
                  ? 'Đã hoàn tất'
                  : 'Các agent đang làm việc'}
              </span>
              {model.questionType && (
                <span className="rounded-md border border-border-default px-1.5 py-px text-xs text-text-secondary">
                  {QUESTION_TYPES[model.questionType] || model.questionType}
                </span>
              )}
              {ready && effectiveReportId && (
                <button
                  type="button"
                  onClick={() => {
                    setStay(true);
                    onOpenReport?.(effectiveReportId);
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-ink px-3 py-1 text-xs font-semibold text-ink-inverse hover:bg-[#3a3a36] shadow-sm transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ml-2"
                >
                  <FileText className="size-3.5" aria-hidden="true" />
                  <span>Mở báo cáo</span>
                  <ArrowRight className="size-3.5" aria-hidden="true" />
                </button>
              )}
            </div>
            <h2 className="font-display mt-2 mb-0 text-[22px] font-bold leading-snug text-balance text-text-primary sm:text-[26px]">
              {query || 'Phiên phân tích'}
            </h2>
          </div>
          <span className="font-mono text-[15px] font-semibold tabular-nums text-text-primary" aria-label="Thời gian đã chạy">
            {clock(elapsed)}
          </span>
        </div>
        <ol className="mt-4 mb-0 grid list-none grid-cols-3 gap-1.5 p-0 sm:grid-cols-6" aria-label="Tiến độ">
          {PHASES.map((label, i) => {
            const state = i < model.phase || model.done ? 'done' : i === model.phase ? 'now' : 'next';
            return (
              <li key={label} className="min-w-0">
                <div
                  className={`h-1 rounded-full ${
                    state === 'done' ? 'bg-text-primary' : state === 'now' ? 'bg-amber agent-phase-now' : 'bg-surface-tertiary'
                  }`}
                />
                <span
                  className={`mt-1.5 block truncate text-xs ${
                    state === 'next' ? 'text-text-tertiary' : 'font-medium text-text-primary'
                  }`}
                  aria-current={state === 'now' ? 'step' : undefined}
                >
                  {label}
                </span>
              </li>
            );
          })}
        </ol>
      </header>

      {/* Agent Pipeline Flow: Non-overlapping responsive cards with clear handoff indication */}
      <div className="border-b border-border-subtle bg-surface-secondary/20 p-4 sm:p-6">
        <div className="flex items-center justify-between pb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Luồng xử lý giữa các agent
          </span>
          <span className="text-xs text-text-tertiary">
            Nhấn vào agent để xem chi tiết
          </span>
        </div>

        <div
          className={`grid gap-3 ${
            model.agents.length <= 2
              ? 'grid-cols-1 sm:grid-cols-2'
              : model.agents.length === 3
              ? 'grid-cols-1 sm:grid-cols-3'
              : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'
          }`}
        >
          {model.agents.map((id) => (
            <AgentCardNode
              key={id}
              id={id}
              snap={model.snapshots[id]}
              elapsed={elapsed}
              isSelected={id === activeAgentId}
              onClick={() => setSelectedAgentId(id)}
            />
          ))}
        </div>

        {/* Visible Handoff Indicator */}
        {lastEnds && live && !model.done && (
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-border-subtle bg-surface-secondary/70 px-3 py-1.5 text-xs text-text-secondary">
            <span className="font-semibold text-text-primary">{who(lastEnds[0])}</span>
            <ArrowRight className="size-3.5 text-accent shrink-0" aria-hidden="true" />
            <span className="font-semibold text-text-primary">{who(lastEnds[1])}</span>
            <span className="text-text-tertiary">·</span>
            <span className="truncate">{packetLabel(last)}</span>
          </div>
        )}
      </div>

      {/* Main Content: Left = Live Work Pane of selected agent; Right = Chronological Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <LiveWorkPane
          agentId={activeAgentId}
          work={currentWork}
          meta={STAGE_AGENTS[activeAgentId]}
          live={live && !model.done && !isDisconnected}
          runningAgentHint={runningAgentHint}
          onResumeAutoFollow={() => setSelectedAgentId(null)}
        />
        <Feed
          steps={visible}
          live={live && !model.done && !isDisconnected}
          ready={ready}
          effectiveReportId={effectiveReportId}
          onOpenReport={onOpenReport}
          onStay={() => setStay(true)}
        />
      </div>

      {(isDisconnected || ready) && (
        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-border-subtle bg-surface-secondary px-5 py-4 sm:px-7">
          {isDisconnected && !ready ? (
            <>
              <span className="text-sm text-text-warning">Mất kết nối. Thử lại</span>
              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border-default bg-surface-primary px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-hover"
                >
                  <RefreshCw className="size-4" aria-hidden="true" />
                  Thử lại
                </button>
              )}
            </>
          ) : (
            <>
              <span className="flex items-center gap-2 text-sm text-text-primary">
                <Check className="size-4 text-success" aria-hidden="true" />
                Báo cáo đã sẵn sàng{live && !stay && autoRedirect !== false ? ' — đang mở…' : ''}
              </span>
              {effectiveReportId && (
                <button
                  type="button"
                  onClick={() => {
                    setStay(true);
                    onOpenReport?.(effectiveReportId);
                  }}
                  className="inline-flex h-10 items-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-ink-inverse hover:bg-[#3a3a36]"
                >
                  Mở báo cáo
                  <ArrowRight className="size-4" aria-hidden="true" />
                </button>
              )}
            </>
          )}
        </footer>
      )}
    </section>
  );
};

function AgentCardNode({
  id,
  snap,
  elapsed,
  isSelected,
  onClick
}: {
  id: StageAgentId;
  snap: ReturnType<typeof deriveStage>['snapshots'][StageAgentId];
  elapsed: number;
  isSelected: boolean;
  onClick: () => void;
}) {
  const meta = STAGE_AGENTS[id];
  const Icon = ICONS[id];
  const busy = snap.state === 'busy' || snap.state === 'fixing';
  const hub = id === 'orchestrator';

  const tone = isSelected
    ? 'border-accent ring-2 ring-accent/30 bg-surface-primary shadow-sm'
    : snap.state === 'blocked'
    ? 'border-danger/60 bg-danger/5'
    : snap.state === 'fixing'
    ? 'border-warning bg-surface-primary'
    : busy
    ? 'border-amber bg-surface-primary'
    : snap.state === 'done'
    ? 'border-border-default bg-surface-primary hover:border-border-strong'
    : 'border-border-subtle bg-surface-secondary/30 hover:border-border-default';

  return (
    <div
      role="region"
      aria-label={meta.ariaName}
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      className={`relative cursor-pointer rounded-xl border p-3.5 transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${tone} ${
        snap.state === 'unused' ? 'opacity-50' : ''
      }`}
    >
      <div className="flex items-center gap-2.5">
        <span
          className={`grid size-8 shrink-0 place-items-center rounded-lg ${
            isSelected
              ? 'bg-accent text-white'
              : snap.state === 'blocked'
              ? 'bg-danger/15 text-danger'
              : hub
              ? 'bg-ink text-amber'
              : busy
              ? 'bg-amber-soft text-text-accent'
              : 'bg-surface-secondary text-text-secondary'
          }`}
        >
          <Icon className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-1">
            <p className="m-0 truncate text-[13px] font-semibold text-text-primary">{meta.name}</p>
            {isSelected && (
              <span className="size-1.5 rounded-full bg-accent shrink-0" title="Đang xem" />
            )}
          </div>
          <p className="m-0 flex items-center gap-1.5 text-xs">
            <span
              className={
                snap.state === 'done'
                  ? 'text-text-success font-medium'
                  : snap.state === 'blocked'
                  ? 'text-text-danger font-medium'
                  : snap.state === 'fixing'
                  ? 'text-text-warning font-medium'
                  : busy
                  ? 'text-text-accent font-medium'
                  : 'text-text-tertiary'
              }
            >
              {STATE_LABEL[snap.state]}
            </span>
            {busy && <span className="font-mono tabular-nums text-text-tertiary">{clock(elapsed - snap.sinceMs)}</span>}
            {busy && (
              <span className="agent-typing flex gap-0.5" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Real-data generated short summary line */}
      {snap.summaryLine && (
        <p className="mt-1.5 mb-0 text-[11px] font-medium text-text-secondary line-clamp-1" title={snap.summaryLine}>
          {snap.summaryLine}
        </p>
      )}

      <p className="mt-1 mb-0 line-clamp-2 text-xs leading-snug text-text-tertiary">{snap.activity}</p>
      {snap.stats.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {snap.stats.map((s) => (
            <span
              key={s}
              className="rounded-md bg-surface-secondary px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-text-primary"
            >
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function LiveWorkPane({
  agentId,
  work,
  meta,
  live,
  runningAgentHint,
  onResumeAutoFollow
}: {
  agentId: StageAgentId;
  work: AgentWorkData;
  meta: (typeof STAGE_AGENTS)[StageAgentId];
  live: boolean;
  runningAgentHint?: StageAgentId | null;
  onResumeAutoFollow?: () => void;
}) {
  const Icon = ICONS[agentId];

  return (
    <div
      role="region"
      aria-label={`Chi tiết hoạt động của ${meta.name}`}
      className="border-b border-border-subtle p-4 sm:p-6 lg:border-b-0 lg:border-r space-y-4"
    >
      {/* Auto-follow switch hint */}
      {runningAgentHint && (
        <button
          type="button"
          onClick={onResumeAutoFollow}
          className="flex w-full items-center justify-between rounded-xl border border-amber/40 bg-amber-soft/40 px-3.5 py-2 text-xs text-text-accent transition-colors hover:bg-amber-soft"
        >
          <span className="flex items-center gap-1.5 font-medium">
            <span className="size-1.5 rounded-full bg-amber animate-ping" />
            Đang chạy ở {STAGE_AGENTS[runningAgentHint].name}
          </span>
          <span className="text-[11px] font-semibold underline">Nhấn để theo dõi</span>
        </button>
      )}
      {/* Pane Header */}
      <div className="flex items-center justify-between gap-2 border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-lg bg-surface-secondary text-text-primary">
            <Icon className="size-4" aria-hidden="true" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="m-0 text-sm font-semibold text-text-primary">{meta.name}</h3>
              <span className="text-[11px] rounded-md border border-border-default px-1.5 py-0.5 text-text-secondary">
                {agentId === 'orchestrator'
                  ? 'Điều phối'
                  : agentId === 'verifier'
                  ? 'Kiểm định'
                  : agentId === 'critic'
                  ? 'Phản biện'
                  : 'Chuyên viên'}
              </span>
            </div>
            <p className="m-0 text-xs text-text-secondary">{meta.role}</p>
          </div>
        </div>
        {live && work.isTyping && (
          <span
            className="inline-flex items-center gap-1.5 rounded-full bg-amber-soft px-2.5 py-1 text-xs font-semibold text-text-accent"
            aria-live="polite"
          >
            <span className="size-1.5 rounded-full bg-amber animate-ping" />
            Đang viết trực tiếp...
          </span>
        )}
      </div>

      {/* Refusal / Blocked Notice */}
      {work.refusalReason && (
        <div className="rounded-xl border border-danger/30 bg-danger/5 p-4 text-xs space-y-1.5">
          <div className="flex items-center gap-2 text-text-danger font-semibold">
            <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
            <span>Yêu cầu bị từ chối / Ngoài phạm vi phân tích</span>
          </div>
          <p className="m-0 text-text-primary leading-relaxed">{work.refusalReason}</p>
        </div>
      )}

      {/* Unused Agent Notice */}
      {work.isUnused && !work.refusalReason && (
        <div className="rounded-xl border border-border-subtle bg-surface-secondary/40 p-4 text-xs text-text-secondary leading-relaxed">
          Agent này không tham gia vào câu hỏi này (không yêu cầu nhiệm vụ trong kế hoạch phân tích).
        </div>
      )}

      {/* Structured views per agent role (hidden when refused/blocked to avoid misleading placeholders) */}
      {!work.refusalReason && agentId === 'orchestrator' && <OrchestratorView work={work} live={live} />}
      {!work.refusalReason && (agentId === 'company' || agentId === 'sector' || agentId === 'macro') && (
        <SpecialistView work={work} live={live} />
      )}
      {!work.refusalReason && agentId === 'verifier' && <VerifierView work={work} />}
      {!work.refusalReason && agentId === 'critic' && <CriticView work={work} live={live} />}
    </div>
  );
}

/** 1. Orchestrator Detail View */
function OrchestratorView({ work, live }: { work: AgentWorkData; live: boolean }) {
  const plan = work.planSummary;
  const hasPlan = Boolean(plan && (plan.questionType || plan.entities?.length || plan.metrics?.length));

  return (
    <div className="space-y-3">
      {/* Kế hoạch phân tích */}
      <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
        <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <div className="flex items-center gap-2">
            <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
            <span>Kế hoạch phân tích</span>
          </div>
          {plan?.questionType && (
            <span className="rounded bg-surface-secondary px-2 py-0.5 text-[11px] font-medium text-text-primary">
              {QUESTION_TYPES[plan.questionType] || plan.questionType}
            </span>
          )}
        </summary>
        <div className="border-t border-border-subtle p-3 space-y-2.5 text-xs">
          {hasPlan ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <div className="rounded-lg border border-border-subtle bg-surface-primary p-2.5">
                  <span className="text-[11px] font-medium text-text-tertiary block">Dạng câu hỏi</span>
                  <span className="font-semibold text-text-primary mt-0.5 block">
                    {plan?.questionType ? (QUESTION_TYPES[plan.questionType] || plan.questionType) : 'Chưa có'}
                  </span>
                </div>
                <div className="rounded-lg border border-border-subtle bg-surface-primary p-2.5">
                  <span className="text-[11px] font-medium text-text-tertiary block">Ngân hàng</span>
                  <span className="font-semibold text-text-primary mt-0.5 block truncate">
                    {plan?.entities && plan.entities.length > 0 ? plan.entities.join(', ') : 'Toàn ngành'}
                  </span>
                </div>
                <div className="rounded-lg border border-border-subtle bg-surface-primary p-2.5">
                  <span className="text-[11px] font-medium text-text-tertiary block">Kỳ báo cáo</span>
                  <span className="font-semibold text-text-primary mt-0.5 block truncate">
                    {plan?.periods && plan.periods.length > 0 ? plan.periods.join(', ') : 'Chưa có'}
                  </span>
                </div>
              </div>

              {plan?.metrics && plan.metrics.length > 0 && (
                <div className="rounded-lg border border-border-subtle bg-surface-primary p-2.5">
                  <span className="text-[11px] font-medium text-text-tertiary block mb-1">Chỉ tiêu phân tích</span>
                  <div className="flex flex-wrap gap-1">
                    {plan.metrics.map((m) => (
                      <span
                        key={m}
                        className="rounded bg-surface-secondary px-2 py-0.5 text-[11px] font-medium text-text-primary"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="m-0 text-text-secondary italic">
              {live ? 'Đang phân tích câu hỏi và lập kế hoạch...' : 'Chưa có kế hoạch phân tích.'}
            </p>
          )}
        </div>
      </details>

      {/* Lý do chọn kế hoạch (Rationale) */}
      <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
        <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <div className="flex items-center gap-2">
            <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
            <span>Lý do chọn kế hoạch</span>
          </div>
          <span className="text-[11px] text-text-tertiary font-normal">Căn cứ điều phối</span>
        </summary>
        <div className="border-t border-border-subtle p-3 text-xs">
          {plan?.rationale ? (
            <div className="rounded-lg border-l-2 border-accent bg-surface-primary p-3 text-text-primary leading-relaxed">
              {plan.rationale}
            </div>
          ) : (
            <p className="m-0 text-text-secondary italic">
              {live ? 'Đang xác định căn cứ lập kế hoạch...' : 'Chưa có thông tin lý do chọn kế hoạch.'}
            </p>
          )}
        </div>
      </details>

      {/* Phân công nhiệm vụ & Công cụ đã giao */}
      <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
        <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <div className="flex items-center gap-2">
            <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
            <span>Nhiệm vụ & Công cụ đã giao</span>
          </div>
          <span className="text-[11px] font-normal text-text-secondary">
            {plan?.assignments?.length ? `${plan.assignments.length} nhiệm vụ` : 'Phân công'}
          </span>
        </summary>
        <div className="border-t border-border-subtle p-3 space-y-2 text-xs">
          {plan?.assignments && plan.assignments.length > 0 ? (
            <div className="space-y-2">
              {plan.assignments.map((asgn, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-border-subtle bg-surface-primary p-2.5 space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-text-primary">{asgn.agentName}</span>
                    <span className="rounded bg-surface-secondary px-1.5 py-0.5 text-[10px] font-mono text-text-secondary">
                      {asgn.agent}
                    </span>
                  </div>
                  <p className="m-0 text-text-secondary">{asgn.task}</p>
                  {asgn.tools && asgn.tools.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {asgn.tools.map((t, idx) => {
                        const label = typeof t === 'string' ? t : (t as { label?: string; tool?: string }).label || (t as { label?: string; tool?: string }).tool || String(t);
                        return (
                          <span
                            key={idx}
                            className="rounded bg-surface-secondary px-1.5 py-0.5 text-[10px] font-mono text-text-tertiary"
                          >
                            {label}
                          </span>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : plan?.tools && plan.tools.length > 0 ? (
            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-text-tertiary block">Công cụ được giao:</span>
              <div className="flex flex-wrap gap-1.5">
                {plan.tools.map((t, idx) => {
                  const label = typeof t === 'string' ? t : (t as { label?: string; tool?: string }).label || (t as { label?: string; tool?: string }).tool || String(t);
                  return (
                    <span
                      key={idx}
                      className="rounded bg-surface-primary border border-border-subtle px-2 py-0.5 text-xs font-mono text-text-primary"
                    >
                      {label}
                    </span>
                  );
                })}
              </div>
            </div>
          ) : (
            <p className="m-0 text-text-secondary italic">
              {live ? 'Đang phân công công cụ cho các chuyên viên...' : 'Chưa phân công công cụ.'}
            </p>
          )}
        </div>
      </details>

      {/* Bản nháp tổng hợp (nếu có) */}
      {work.draftText && (
        <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
          <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
            <div className="flex items-center gap-2">
              <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
              <span>Bản nháp tổng hợp</span>
            </div>
            {work.isTyping && (
              <span className="text-[11px] text-text-accent font-medium">đang viết...</span>
            )}
          </summary>
          <div className="border-t border-border-subtle p-3 text-xs">
            <div className="rounded-lg border border-border-subtle bg-surface-primary p-3 text-[13px] leading-relaxed text-text-primary whitespace-pre-wrap select-text">
              {work.draftText}
              {work.isTyping && (
                <span className="inline-block w-1.5 h-3.5 ml-1 bg-amber animate-pulse align-middle" aria-hidden="true" />
              )}
            </div>
          </div>
        </details>
      )}
    </div>
  );
}

/** 2. Specialist Detail View (Company, Sector, Macro) */
function SpecialistView({
  work,
  live
}: {
  work: AgentWorkData;
  live: boolean;
}) {
  const keptVerdicts = work.verdicts.filter((v) => v.verdict === 'kept');
  const droppedVerdicts = work.verdicts.filter((v) => v.verdict === 'dropped');

  return (
    <div className="space-y-3">
      {/* Section 1: Phép phân tích đã chạy & Số liệu trả về */}
      <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
        <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <div className="flex items-center gap-2">
            <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
            <span>Truy vấn dữ liệu ({work.toolCalls.length})</span>
          </div>
          <span className="text-[11px] font-normal text-text-secondary">
            {work.facts.length > 0 ? `${work.facts.length} số liệu có nguồn` : `${work.toolCalls.length} phép tính`}
          </span>
        </summary>
        <div className="border-t border-border-subtle p-3 space-y-3 text-xs">
          {work.toolCalls.length > 0 ? (
            <div className="space-y-2">
              {work.toolCalls.map((t, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-border-subtle bg-surface-primary p-2.5 space-y-1.5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-text-primary">{t.tool}</span>
                      {t.label && (
                        <span className="text-[11px] text-text-secondary">({t.label})</span>
                      )}
                      {t.status === 'running' && (
                        <span className="rounded bg-amber-soft px-1.5 py-0.5 text-[10px] font-medium text-text-accent">
                          Đang chạy
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-text-tertiary">
                      {t.resultCount !== undefined && (
                        <span className="font-semibold text-text-primary tabular-nums">
                          {t.resultCount} số liệu
                        </span>
                      )}
                      {t.durationMs !== undefined && (
                        <span className="font-mono tabular-nums">{t.durationMs}ms</span>
                      )}
                    </div>
                  </div>

                  {t.arguments && (
                    <div className="flex flex-wrap gap-2 text-[11px] text-text-secondary pt-0.5">
                      {t.arguments.entities && t.arguments.entities.length > 0 && (
                        <span>NH: <strong className="text-text-primary">{t.arguments.entities.join(', ')}</strong></span>
                      )}
                      {t.arguments.metrics && t.arguments.metrics.length > 0 && (
                        <span>Chỉ tiêu: <strong className="text-text-primary">{t.arguments.metrics.join(', ')}</strong></span>
                      )}
                      {t.arguments.periods && t.arguments.periods.length > 0 && (
                        <span>Kỳ: <strong className="text-text-primary">{t.arguments.periods.join(', ')}</strong></span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="m-0 text-text-secondary italic">
              {live ? 'Đang truy vấn dữ liệu từ kho...' : 'Chưa có phép phân tích nào được chạy.'}
            </p>
          )}

          {/* Sourced Facts List (Số liệu có nguồn gốc) */}
          {work.facts.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Số liệu có nguồn ({work.facts.length})
                </span>
                <span className="text-[10px] text-text-tertiary">Đối chiếu báo cáo gốc</span>
              </div>
              <div className="max-h-[160px] overflow-y-auto space-y-1 pr-1">
                {work.facts.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between gap-2 rounded border border-border-subtle bg-surface-secondary/40 px-2.5 py-1.5 text-[11px]"
                  >
                    <span className="text-text-primary truncate">{f.label}</span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="font-bold text-text-primary tabular-nums">{f.displayValue}</span>
                      {f.sourceNoteNo && (
                        <span
                          className="rounded bg-surface-tertiary px-1 py-0.2 text-[9px] font-medium text-text-secondary"
                          title="Ghi chú BCTC số"
                        >
                          Ghi chú {f.sourceNoteNo}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </details>

      {/* Section 2: Nhận định đã viết & Kết quả kiểm định từng câu */}
      <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
        <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <div className="flex items-center gap-2">
            <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
            <span>
              {work.verdicts.length > 0
                ? `Kết quả kiểm định từng câu (${work.verdicts.length})`
                : 'Bản nháp nhận định'}
            </span>
          </div>
          {work.verdicts.length > 0 ? (
            <span className="text-[11px] font-medium text-text-secondary">
              {keptVerdicts.length} đạt · {droppedVerdicts.length} loại
            </span>
          ) : work.isTyping ? (
            <span className="text-[11px] text-text-accent font-medium">đang truyền dòng văn bản...</span>
          ) : null}
        </summary>
        <div className="border-t border-border-subtle p-3 space-y-2.5 text-xs">
          {/* Live Streaming Prose */}
          {work.draftText && !work.verdicts.length && (
            <div className="space-y-2">
              <h4 className="m-0 text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Nội dung nhận định
              </h4>
              <div
                className="rounded-xl border border-border-subtle bg-surface-secondary/40 p-3.5 text-[13px] leading-relaxed text-text-primary whitespace-pre-wrap font-sans select-text"
                aria-live="polite"
              >
                {work.draftText}
                {work.isTyping && (
                  <span className="inline-block w-1.5 h-3.5 ml-1 bg-amber animate-pulse align-middle" aria-hidden="true" />
                )}
              </div>
            </div>
          )}

          {/* Verdicts List */}
          {work.verdicts.length > 0 ? (
            <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
              {work.verdicts.map((v, i) => (
                <div
                  key={i}
                  className={`rounded-lg border p-2.5 text-xs transition-colors ${
                    v.verdict === 'kept'
                      ? 'border-success/30 bg-success-soft/20 text-text-primary'
                      : 'border-danger/30 bg-danger-soft/20 text-text-tertiary'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span
                      className={`mt-0.5 grid size-4 shrink-0 place-items-center rounded-full text-[10px] font-bold ${
                        v.verdict === 'kept' ? 'bg-success text-white' : 'bg-danger text-white'
                      }`}
                    >
                      {v.verdict === 'kept' ? '✓' : '✗'}
                    </span>
                    <div className="min-w-0 flex-1 space-y-1">
                      <p className={`m-0 leading-snug ${v.verdict === 'dropped' ? 'line-through decoration-danger/60' : ''}`}>
                        {v.sentence}
                      </p>
                      {v.verdict === 'dropped' && (
                        <p className="m-0 text-[11px] font-medium text-danger">
                          Lý do: {v.explanationVi || v.dropReason || 'Không đủ căn cứ kiểm chứng'}
                        </p>
                      )}
                      {v.factIds && v.factIds.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-0.5">
                          {v.factIds.map((fid) => (
                            <span
                              key={fid}
                              className="rounded bg-surface-primary border border-border-subtle px-1.5 py-px text-[10px] font-mono text-text-secondary"
                            >
                              {fid}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : !work.draftText ? (
            <p className="m-0 text-text-secondary italic">
              {live ? 'Đang viết nhận định từ số liệu...' : 'Chưa có nhận định nào được tạo.'}
            </p>
          ) : null}
        </div>
      </details>
    </div>
  );
}

/** 3. Verifier Detail View */
function VerifierView({ work }: { work: AgentWorkData }) {
  const stats = work.verifierStats;
  const dropped = work.verdicts.filter((v) => v.verdict === 'dropped');
  const kept = work.verdicts.filter((v) => v.verdict === 'kept');

  return (
    <div className="space-y-3">
      {/* Tổng hợp kiểm định số liệu */}
      <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
        <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <div className="flex items-center gap-2">
            <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
            <span>Tổng hợp kiểm định số liệu</span>
          </div>
          <span className="text-[11px] font-medium text-text-secondary">
            {stats.numbersChecked > 0 ? `${stats.numbersMatched}/${stats.numbersChecked} số khớp` : 'Kiểm tra số'}
          </span>
        </summary>
        <div className="border-t border-border-subtle p-3 space-y-2 text-xs">
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-lg border border-border-subtle bg-surface-primary p-2.5 text-center">
              <span className="text-[11px] font-medium text-text-tertiary block">Số câu đã kiểm</span>
              <span className="font-bold text-text-primary text-base mt-0.5 block tabular-nums">
                {stats.sentencesChecked || work.verdicts.length}
              </span>
            </div>
            <div className="rounded-lg border border-border-subtle bg-surface-primary p-2.5 text-center">
              <span className="text-[11px] font-medium text-text-tertiary block">Số liệu khớp</span>
              <span className="font-bold text-success text-base mt-0.5 block tabular-nums">
                {stats.numbersChecked > 0 ? `${stats.numbersMatched}/${stats.numbersChecked}` : '0/0'}
              </span>
            </div>
            <div className="rounded-lg border border-border-subtle bg-surface-primary p-2.5 text-center">
              <span className="text-[11px] font-medium text-text-tertiary block">Câu bị loại</span>
              <span
                className={`font-bold text-base mt-0.5 block tabular-nums ${
                  stats.droppedCount > 0 ? 'text-danger' : 'text-text-primary'
                }`}
              >
                {stats.droppedCount}
              </span>
            </div>
          </div>
        </div>
      </details>

      {/* Các câu bị loại & Lý do */}
      <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
        <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <div className="flex items-center gap-2">
            <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
            <span>Các câu bị loại ({dropped.length})</span>
          </div>
          <span className="text-[11px] font-normal text-text-secondary">
            {dropped.length > 0 ? `${dropped.length} câu không đạt` : 'Không có'}
          </span>
        </summary>
        <div className="border-t border-border-subtle p-3 space-y-2 text-xs">
          {dropped.length > 0 ? (
            <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
              {dropped.map((v, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-danger/30 bg-danger-soft/20 p-2.5 space-y-1 text-xs"
                >
                  <p className="m-0 text-text-tertiary line-through decoration-danger/60 leading-snug">
                    {v.sentence}
                  </p>
                  <p className="m-0 text-[11px] font-medium text-danger">
                    Lý do loại: {v.explanationVi || v.dropReason || 'Số liệu không khớp với dữ liệu gốc'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="m-0 text-text-success font-medium flex items-center gap-1.5">
              <Check className="size-3.5 text-success" />
              Không có nhận định nào bị loại. Tất cả câu có số liệu đều khớp với dữ liệu gốc.
            </p>
          )}
        </div>
      </details>

      {/* Chi tiết từng câu kiểm định */}
      {work.verdicts.length > 0 && (
        <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
          <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
            <div className="flex items-center gap-2">
              <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
              <span>Kết quả kiểm định từng câu ({work.verdicts.length})</span>
            </div>
            <span className="text-[11px] text-text-tertiary">
              ✓ {kept.length} đạt · ✗ {dropped.length} loại
            </span>
          </summary>
          <div className="border-t border-border-subtle p-3 space-y-2 text-xs max-h-[240px] overflow-y-auto pr-1">
            {work.verdicts.map((v, i) => (
              <div
                key={i}
                className={`rounded-lg border p-2 text-xs flex items-start gap-2 ${
                  v.verdict === 'kept'
                    ? 'border-success/30 bg-success-soft/20 text-text-primary'
                    : 'border-danger/30 bg-danger-soft/20 text-text-tertiary'
                }`}
              >
                <span
                  className={`mt-0.5 grid size-3.5 shrink-0 place-items-center rounded-full text-[9px] font-bold ${
                    v.verdict === 'kept' ? 'bg-success text-white' : 'bg-danger text-white'
                  }`}
                >
                  {v.verdict === 'kept' ? '✓' : '✗'}
                </span>
                <div className="min-w-0 flex-1 space-y-0.5">
                  <p className={`m-0 leading-snug ${v.verdict === 'dropped' ? 'line-through decoration-danger/60' : ''}`}>
                    {v.sentence}
                  </p>
                  {v.verdict === 'dropped' && (
                    <p className="m-0 text-[10px] font-medium text-danger">
                      Lý do: {v.explanationVi || v.dropReason || 'Không đủ căn cứ kiểm chứng'}
                    </p>
                  )}
                  {v.factIds && v.factIds.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-0.5">
                      {v.factIds.map((fid) => (
                        <span
                          key={fid}
                          className="rounded bg-surface-primary border border-border-subtle px-1 py-px text-[9px] font-mono text-text-secondary"
                        >
                          {fid}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

/** 4. Critic Detail View */
function CriticView({ work, live }: { work: AgentWorkData; live: boolean }) {
  const issues = work.issues;
  const revisions = work.revisions;
  const accepted = work.criticAccepted;

  return (
    <div className="space-y-3">
      {/* Section 1: Tiến trình phản biện theo vòng */}
      <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
        <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <div className="flex items-center gap-2">
            <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
            <span>Tiến trình phản biện</span>
          </div>
          <span className="text-[11px] font-medium text-text-secondary">
            {issues.length > 0 ? `${issues.length} yêu cầu sửa` : 'Rà soát lập luận'}
          </span>
        </summary>
        <div className="border-t border-border-subtle p-3 text-xs space-y-2">
          {accepted ? (
            <div className="rounded-lg border border-success/30 bg-success-soft/20 p-2.5 flex items-center gap-2 text-text-primary">
              <Check className="size-4 text-success shrink-0" />
              <span>{accepted}</span>
            </div>
          ) : issues.length > 0 ? (
            <p className="m-0 text-text-secondary leading-relaxed">
              Phản biện đã kiểm tra chéo các nhận định và gửi {issues.length} yêu cầu sửa đổi logic và tính bao quát.
            </p>
          ) : (
            <p className="m-0 text-text-secondary italic">
              {live ? 'Đang kiểm tra chéo lập luận giữa các agent...' : 'Chưa có lượt phản biện.'}
            </p>
          )}
        </div>
      </details>

      {/* Section 2: Vấn đề đã nêu & Yêu cầu sửa */}
      <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
        <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <div className="flex items-center gap-2">
            <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
            <span>Vấn đề & Yêu cầu sửa ({issues.length})</span>
          </div>
          <span className="text-[11px] font-normal text-text-secondary">
            {issues.length > 0 ? `${issues.length} góp ý` : 'Không có'}
          </span>
        </summary>
        <div className="border-t border-border-subtle p-3 space-y-2 text-xs">
          {issues.length > 0 ? (
            <div className="space-y-2 max-h-[240px] overflow-y-auto pr-1">
              {issues.map((iss, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-warning/40 bg-warning-soft/20 p-2.5 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 font-semibold text-warning">
                      <AlertCircle className="size-3.5 shrink-0" />
                      <span>{iss.requiredAction || 'Yêu cầu sửa đổi'}</span>
                    </div>
                    {iss.severity && (
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                          iss.severity === 'MAJOR'
                            ? 'bg-danger/20 text-danger'
                            : 'bg-warning/20 text-warning'
                        }`}
                      >
                        {iss.severity}
                      </span>
                    )}
                  </div>
                  <p className="m-0 text-text-primary leading-snug">{iss.description}</p>
                  {iss.targetSentence && (
                    <p className="m-0 text-text-tertiary text-[11px] italic bg-surface-primary/60 rounded p-1.5 border border-border-subtle">
                      &ldquo;{iss.targetSentence}&rdquo;
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="m-0 text-text-secondary italic">Không có yêu cầu sửa đổi nào.</p>
          )}
        </div>
      </details>

      {/* Section 3: Kết quả sau sửa (Hiệu chỉnh) */}
      <details open className="group rounded-xl border border-border-subtle bg-surface-secondary/20 overflow-hidden">
        <summary className="flex cursor-pointer items-center justify-between p-3 text-xs font-semibold text-text-primary hover:bg-surface-secondary/50 transition-colors select-none focus:outline-none focus-visible:ring-1 focus-visible:ring-accent">
          <div className="flex items-center gap-2">
            <ChevronDown className="size-3.5 text-text-tertiary transition-transform group-open:rotate-180" />
            <span>Kết quả sau sửa ({revisions.length})</span>
          </div>
          <span className="text-[11px] font-normal text-text-secondary">
            {revisions.length > 0 ? `${revisions.length} bản sửa` : 'Không có'}
          </span>
        </summary>
        <div className="border-t border-border-subtle p-3 space-y-2 text-xs">
          {revisions.length > 0 ? (
            <div className="space-y-2 max-h-[240px] overflow-y-auto pr-1">
              {revisions.map((rev, i) => (
                <div
                  key={i}
                  className="space-y-1.5 rounded-lg border border-border-subtle bg-surface-primary p-2.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-semibold text-text-tertiary uppercase">Hiệu chỉnh câu</span>
                    {rev.verified && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-success">
                        <Check className="size-3" />
                        Đã kiểm định lại
                      </span>
                    )}
                  </div>
                  {rev.before && (
                    <p className="m-0 text-text-tertiary line-through decoration-danger/60 leading-snug">
                      {readerText(rev.before)}
                    </p>
                  )}
                  {rev.after && (
                    <p className="m-0 font-medium text-text-primary leading-snug">
                      {readerText(rev.after)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="m-0 text-text-secondary italic">Chưa có bản sửa đổi nào.</p>
          )}
        </div>
      </details>
    </div>
  );
}

const KIND_ICON: Partial<Record<TraceStep['kind'], LucideIcon>> = {
  plan: Network,
  assign: ArrowRight,
  tool_result: Sigma,
  draft: PencilLine,
  verify: BookOpenCheck,
  compose: FileText,
  critique_issue: ShieldCheck,
  revision: PencilLine,
  accept: Check,
  report_ready: Check
};

function Feed({
  steps,
  live,
  ready,
  effectiveReportId,
  onOpenReport,
  onStay
}: {
  steps: TraceStep[];
  live: boolean;
  ready: boolean;
  effectiveReportId: string | null;
  onOpenReport?: (reportId: string) => void;
  onStay?: () => void;
}) {
  const listRef = useRef<HTMLOListElement>(null);
  const isAtBottomRef = useRef(true);

  const handleScroll = () => {
    const el = listRef.current;
    if (!el) return;
    const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    isAtBottomRef.current = distanceToBottom < 30;
  };

  useEffect(() => {
    const el = listRef.current;
    if (el && isAtBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [steps.length]);

  return (
    <div className="flex min-h-0 flex-col">
      <div className="flex items-center justify-between px-5 pt-4 pb-2 sm:px-6">
        <h3 className="m-0 text-[13px] font-semibold text-text-primary">Nhật ký trao đổi</h3>
        <span className="text-xs tabular-nums text-text-tertiary">{steps.length} bước</span>
      </div>
      <ol
        ref={listRef}
        onScroll={handleScroll}
        className="m-0 max-h-[440px] list-none space-y-3 overflow-y-auto px-5 pb-5 sm:px-6"
        aria-live="polite"
      >
        {steps.length === 0 && (
          <li className="rounded-xl border border-dashed border-border-default p-4 text-sm text-text-secondary">
            Điều phối viên đang đọc câu hỏi và chọn chuyên viên phù hợp…
          </li>
        )}
        {steps.map((s) => {
          const Icon = KIND_ICON[s.kind] || ArrowRight;
          const to = s.kind === 'draft' ? 'orchestrator' : s.recipient;
          const detail = s.detail || {};
          return (
            <li key={s.step_id} className="agent-msg flex gap-3">
              <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg bg-surface-secondary text-text-secondary">
                <Icon className="size-3.5" aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="m-0 flex flex-wrap items-baseline gap-x-1.5 text-xs text-text-secondary">
                  <span className="font-semibold text-text-primary">{who(s.actor)}</span>
                  {to && to !== 'system' && (
                    <>
                      <span aria-hidden="true">→</span>
                      <span className="font-semibold text-text-primary">{who(to)}</span>
                    </>
                  )}
                  <span className="ml-auto font-mono tabular-nums text-text-tertiary">{clock(s.t_ms)}</span>
                </p>
                <p className="mt-0.5 mb-0 text-[13px] leading-snug text-pretty text-text-primary">{readerText(s.summary)}</p>
                {s.kind === 'verify' && Number(detail.numbers_checked) > 0 && (
                  <div className="mt-1.5 flex items-center gap-2">
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-tertiary">
                      <span
                        className="block h-full rounded-full bg-success"
                        style={{ width: `${(100 * Number(detail.numbers_matched)) / Number(detail.numbers_checked)}%` }}
                      />
                    </span>
                    <span className="text-[11px] tabular-nums text-text-secondary">
                      {String(detail.numbers_matched)}/{String(detail.numbers_checked)}
                    </span>
                  </div>
                )}
                {s.kind === 'revision' && typeof detail.before === 'string' && typeof detail.after === 'string' && (
                  <div className="mt-1.5 space-y-1 rounded-lg bg-surface-secondary p-2 text-xs leading-snug">
                    <p className="m-0 text-text-tertiary line-through decoration-danger/60">{readerText(detail.before)}</p>
                    <p className="m-0 text-text-primary">{readerText(detail.after)}</p>
                  </div>
                )}
              </div>
            </li>
          );
        })}

        {/* Completion prompt in feed */}
        {ready && effectiveReportId && (
          <li className="agent-msg rounded-xl border border-border-default bg-surface-secondary/70 p-3 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="m-0 text-xs font-semibold text-text-primary">Phiên phân tích đã hoàn tất</p>
              <p className="m-0 text-[11px] text-text-secondary truncate">Báo cáo phân tích đã sẵn sàng để xem.</p>
            </div>
            <button
              type="button"
              onClick={() => {
                onStay?.();
                onOpenReport?.(effectiveReportId);
              }}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-ink px-3 py-1.5 text-xs font-semibold text-ink-inverse hover:bg-[#3a3a36] transition-all"
            >
              <span>Mở báo cáo</span>
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </button>
          </li>
        )}

        {live && steps.length > 0 && !ready && (
          <li className="flex items-center gap-2 pl-10 text-xs text-text-tertiary" aria-hidden="true">
            <span className="agent-typing flex gap-0.5">
              <i />
              <i />
              <i />
            </span>
            đang làm việc
          </li>
        )}
      </ol>
    </div>
  );
}
