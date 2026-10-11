import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowRight,
  BookOpenCheck,
  Building2,
  Check,
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
  deriveStage,
  deriveAgentWork,
  readerText,
  stepEndpoints,
  type AgentWorkData,
  type StageAgentId,
  type StageAgentState
} from '../model/agentStage';

export interface AgentStageProps {
  steps: TraceStep[];
  query?: string;
  live?: boolean;
  reportId?: string | null;
  isDisconnected?: boolean;
  liveWorkState?: LiveWorkState;
  onOpenReport?: (reportId: string) => void;
  onRetry?: () => void;
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
  unused: 'Không dùng đến'
};

const QUESTION_TYPES: Record<string, string> = {
  lookup: 'Tra cứu',
  company_profile: 'Hồ sơ doanh nghiệp',
  ranking: 'Xếp hạng',
  trend: 'Xu hướng',
  head_to_head: 'So sánh trực tiếp',
  sector_theme: 'Toàn ngành',
  relationship: 'Tương quan'
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
  onRetry
}) => {
  // Steps often arrive in bursts; reveal them one by one so every hand-off is visible.
  const [shown, setShown] = useState(() => (live ? 0 : steps.length));
  useEffect(() => {
    if (shown >= steps.length) return;
    const delay = prefersReducedMotion() || !live ? 0 : shown === 0 ? 120 : 700;
    const t = setTimeout(() => setShown((n) => Math.min(n + 1, steps.length)), delay);
    return () => clearTimeout(t);
  }, [shown, steps.length, live]);

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
  const ready = model.done && Boolean(effectiveReportId);
  const [stay, setStay] = useState(false);
  useEffect(() => {
    if (!ready || !effectiveReportId || stay || !onOpenReport || !live) return;
    const t = setTimeout(() => onOpenReport(effectiveReportId), prefersReducedMotion() ? 0 : 1800);
    return () => clearTimeout(t);
  }, [ready, effectiveReportId, stay, onOpenReport, live]);

  // Selected agent for inspection; defaults to currently active agent
  const [selectedAgentId, setSelectedAgentId] = useState<StageAgentId | null>(null);

  const activeAgentId: StageAgentId = useMemo(() => {
    if (selectedAgentId && model.agents.includes(selectedAgentId)) {
      return selectedAgentId;
    }
    if (liveWorkState?.activeWriterRole && model.agents.includes(liveWorkState.activeWriterRole as StageAgentId)) {
      return liveWorkState.activeWriterRole as StageAgentId;
    }
    // Find first busy or fixing agent
    const working = model.agents.find(
      (a) => model.snapshots[a].state === 'busy' || model.snapshots[a].state === 'fixing'
    );
    if (working) return working;

    // If all done, prefer specialist or orchestrator
    const specialist = model.agents.find((a) => a === 'company' || a === 'sector');
    if (specialist && model.snapshots[specialist].state === 'done') return specialist;

    return model.agents[0] || 'orchestrator';
  }, [selectedAgentId, liveWorkState?.activeWriterRole, model.agents, model.snapshots]);

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
            <p className="m-0 flex items-center gap-2 text-[13px] text-text-secondary">
              <span
                className={`size-2 rounded-full ${
                  isDisconnected
                    ? 'bg-warning'
                    : model.done
                    ? 'bg-success'
                    : 'bg-amber agent-live-dot'
                }`}
                aria-hidden="true"
              />
              {isDisconnected ? 'Mất kết nối' : model.done ? 'Đã hoàn tất' : 'Các tác tử đang làm việc'}
              {model.questionType && (
                <span className="rounded-md border border-border-default px-1.5 py-px text-xs text-text-secondary">
                  {QUESTION_TYPES[model.questionType] || model.questionType}
                </span>
              )}
            </p>
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
            Luồng xử lý giữa các tác tử
          </span>
          <span className="text-xs text-text-tertiary">
            Nhấn vào tác tử để xem chi tiết
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
        />
        <Feed steps={visible} live={live && !model.done && !isDisconnected} />
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
                Báo cáo đã sẵn sàng{live && !stay ? ' — đang mở…' : ''}
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
      <p className="mt-2 mb-0 line-clamp-2 text-xs leading-snug text-text-secondary">{snap.activity}</p>
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
  live
}: {
  agentId: StageAgentId;
  work: AgentWorkData;
  meta: typeof STAGE_AGENTS[StageAgentId];
  live: boolean;
}) {
  const Icon = ICONS[agentId];
  const hasContent =
    Boolean(work.draftText) ||
    work.verdicts.length > 0 ||
    work.toolCalls.length > 0 ||
    work.issues.length > 0 ||
    work.revisions.length > 0 ||
    Boolean(work.planSummary && agentId === 'orchestrator');

  return (
    <div
      role="region"
      aria-label={`Chi tiết hoạt động của ${meta.name}`}
      className="border-b border-border-subtle p-4 sm:p-6 lg:border-b-0 lg:border-r space-y-4"
    >
      {/* Pane Header */}
      <div className="flex items-center justify-between gap-2 border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2">
          <span className="grid size-7 place-items-center rounded-lg bg-surface-secondary text-text-primary">
            <Icon className="size-4" aria-hidden="true" />
          </span>
          <div>
            <h3 className="m-0 text-sm font-semibold text-text-primary">{meta.name}</h3>
            <p className="m-0 text-xs text-text-secondary">{meta.role}</p>
          </div>
        </div>
        {work.isTyping && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-soft px-2.5 py-1 text-xs font-semibold text-text-accent" aria-live="polite">
            <span className="size-1.5 rounded-full bg-amber animate-ping" />
            Đang viết trực tiếp...
          </span>
        )}
      </div>

      {/* 1. Plan summary (for Orchestrator) */}
      {agentId === 'orchestrator' && work.planSummary && (
        <div className="space-y-2 rounded-xl border border-border-subtle bg-surface-secondary/30 p-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-text-primary">Kế hoạch phân tích</span>
            {work.planSummary.questionType && (
              <span className="rounded bg-surface-secondary px-1.5 py-0.5 font-medium text-text-secondary">
                {QUESTION_TYPES[work.planSummary.questionType] || work.planSummary.questionType}
              </span>
            )}
          </div>
          {work.planSummary.entities && work.planSummary.entities.length > 0 && (
            <p className="m-0 text-text-secondary">
              <span className="text-text-tertiary">Ngân hàng: </span>
              <span className="font-medium text-text-primary">{work.planSummary.entities.join(', ')}</span>
            </p>
          )}
          {work.planSummary.metrics && work.planSummary.metrics.length > 0 && (
            <p className="m-0 text-text-secondary">
              <span className="text-text-tertiary">Chỉ tiêu: </span>
              <span className="font-medium text-text-primary">{work.planSummary.metrics.join(', ')}</span>
            </p>
          )}
          {work.planSummary.periods && work.planSummary.periods.length > 0 && (
            <p className="m-0 text-text-secondary">
              <span className="text-text-tertiary">Kỳ: </span>
              <span className="font-medium text-text-primary">{work.planSummary.periods.join(', ')}</span>
            </p>
          )}
        </div>
      )}

      {/* 2. Draft Prose Streaming */}
      {work.draftText && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="m-0 text-xs font-semibold uppercase tracking-wider text-text-secondary">
              Bản nháp nhận định
            </h4>
            {work.isTyping && (
              <span className="text-[11px] text-text-accent font-medium" aria-live="polite">
                đang truyền dòng văn bản...
              </span>
            )}
          </div>
          <div
            className="rounded-xl border border-border-subtle bg-surface-secondary/40 p-4 text-[13px] leading-relaxed text-text-primary whitespace-pre-wrap font-sans select-text"
            aria-live="polite"
          >
            {work.draftText}
            {work.isTyping && (
              <span className="inline-block w-1.5 h-3.5 ml-1 bg-amber animate-pulse align-middle" aria-hidden="true" />
            )}
          </div>
        </div>
      )}

      {/* 3. Sentence Verdicts */}
      {work.verdicts.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="m-0 text-xs font-semibold uppercase tracking-wider text-text-secondary">
              Kết quả kiểm định từng câu ({work.verdicts.length})
            </h4>
            <span className="text-[11px] text-text-tertiary">
              ✓ Giữ nguyên · ✗ Loại bỏ
            </span>
          </div>
          <div className="space-y-2 max-h-[240px] overflow-y-auto pr-1">
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
        </div>
      )}

      {/* 4. Tool Calls */}
      {work.toolCalls.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="m-0 text-xs font-semibold uppercase tracking-wider text-text-secondary">
              Truy vấn dữ liệu ({work.toolCalls.length})
            </h4>
          </div>
          <div className="space-y-1.5 max-h-[160px] overflow-y-auto pr-1">
            {work.toolCalls.map((t, idx) => (
              <div
                key={idx}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border-subtle bg-surface-secondary/40 px-3 py-2 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono font-medium text-text-primary">{t.tool}</span>
                  {t.status === 'running' && (
                    <span className="rounded bg-amber-soft px-1.5 py-0.5 text-[10px] font-medium text-text-accent">
                      Đang chạy
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-[11px] text-text-tertiary">
                  {t.arguments?.entities && (
                    <span>NH: {t.arguments.entities.join(', ')}</span>
                  )}
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
            ))}
          </div>
        </div>
      )}

      {/* 5. Critique Issues & Revisions */}
      {(work.issues.length > 0 || work.revisions.length > 0) && (
        <div className="space-y-2">
          <h4 className="m-0 text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Phản biện & Hiệu chỉnh
          </h4>
          {work.issues.map((iss, i) => (
            <div key={i} className="rounded-lg border border-warning/40 bg-warning-soft/20 p-2.5 text-xs space-y-1">
              <div className="flex items-center gap-1.5 font-medium text-warning">
                <AlertCircle className="size-3.5" />
                <span>Yêu cầu sửa: {iss.description || iss.requiredAction}</span>
              </div>
              {iss.targetSentence && (
                <p className="m-0 text-text-secondary text-[11px] italic">
                  &ldquo;{iss.targetSentence}&rdquo;
                </p>
              )}
            </div>
          ))}
          {work.revisions.map((rev, i) => (
            <div key={i} className="space-y-1 rounded-lg border border-border-subtle bg-surface-secondary/40 p-2.5 text-xs">
              <span className="text-[10px] font-semibold text-text-tertiary uppercase">Hiệu chỉnh câu</span>
              {rev.before && (
                <p className="m-0 text-text-tertiary line-through decoration-danger/60">{readerText(rev.before)}</p>
              )}
              {rev.after && (
                <p className="m-0 font-medium text-text-primary">{readerText(rev.after)}</p>
              )}
              {rev.verified && (
                <span className="inline-flex items-center gap-1 text-[10px] font-medium text-success">
                  <Check className="size-3" />
                  Đã kiểm định lại
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!hasContent && (
        <div className="rounded-xl border border-dashed border-border-default p-6 text-center text-xs text-text-secondary">
          {live
            ? `${meta.name} đang chờ nhiệm vụ từ tiến trình phân tích...`
            : `Không có dữ liệu chi tiết cho ${meta.name} trong phiên này.`}
        </div>
      )}
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

function Feed({ steps, live }: { steps: TraceStep[]; live: boolean }) {
  const listRef = useRef<HTMLOListElement>(null);
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [steps.length]);

  return (
    <div className="flex min-h-0 flex-col">
      <div className="flex items-center justify-between px-5 pt-4 pb-2 sm:px-6">
        <h3 className="m-0 text-[13px] font-semibold text-text-primary">Nhật ký trao đổi</h3>
        <span className="text-xs tabular-nums text-text-tertiary">{steps.length} bước</span>
      </div>
      <ol ref={listRef} className="m-0 max-h-[440px] list-none space-y-3 overflow-y-auto px-5 pb-5 sm:px-6" aria-live="polite">
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
        {live && steps.length > 0 && (
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
