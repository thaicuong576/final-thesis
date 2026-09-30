import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import {
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
import {
  PHASES,
  STAGE_AGENTS,
  deriveStage,
  readerText,
  stepEndpoints,
  type StageAgentId,
  type StageAgentState
} from '../model/agentStage';

export interface AgentStageProps {
  steps: TraceStep[];
  query?: string;
  live?: boolean;
  reportId?: string | null;
  isDisconnected?: boolean;
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

/** Node centres as fractions of the stage box: orchestrator in the middle, specialists left, checks right. */
function layout(agents: StageAgentId[]): Record<string, { x: number; y: number }> {
  const pos: Record<string, { x: number; y: number }> = { orchestrator: { x: 0.5, y: 0.5 } };
  const place = (ids: StageAgentId[], x: number) => {
    ids.forEach((id, i) => {
      pos[id] = { x, y: ids.length === 1 ? 0.5 : 0.2 + (0.6 * i) / (ids.length - 1) };
    });
  };
  place(agents.filter((a) => STAGE_AGENTS[a].side === 'left'), 0.15);
  place(agents.filter((a) => STAGE_AGENTS[a].side === 'right'), 0.85);
  return pos;
}

export const AgentStage: React.FC<AgentStageProps> = ({
  steps,
  query,
  live = true,
  reportId,
  isDisconnected = false,
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
  const model = useMemo(() => deriveStage(visible), [visible]);
  const last = visible[visible.length - 1];

  // Local seconds counter while the run is live, so waiting on a model still reads as work in progress.
  const [tickMs, setTickMs] = useState(0);
  useEffect(() => {
    if (!live || model.done) return;
    const id = setInterval(() => setTickMs((t) => t + 1000), 1000);
    return () => clearInterval(id);
  }, [live, model.done]);
  const elapsed = model.done || !live ? last?.t_ms ?? 0 : Math.max(last?.t_ms ?? 0, tickMs);

  const effectiveReportId =
    reportId || (steps.find((s) => s.kind === 'report_ready')?.detail?.report_id as string | undefined) || null;
  const ready = model.done && Boolean(effectiveReportId);
  const [stay, setStay] = useState(false);
  useEffect(() => {
    if (!ready || !effectiveReportId || stay || !onOpenReport || !live) return;
    const t = setTimeout(() => onOpenReport(effectiveReportId), prefersReducedMotion() ? 0 : 1800);
    return () => clearTimeout(t);
  }, [ready, effectiveReportId, stay, onOpenReport, live]);

  return (
    <section className="overflow-hidden rounded-2xl border border-border-subtle bg-surface-primary shadow-[0_1px_2px_rgba(29,28,26,0.04),0_20px_44px_-28px_rgba(60,45,20,0.35)]">
      <header className="border-b border-border-subtle px-5 pt-5 pb-4 sm:px-7">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="m-0 flex items-center gap-2 text-[13px] text-text-secondary">
              <span
                className={`size-2 rounded-full ${model.done ? 'bg-success' : 'bg-amber agent-live-dot'}`}
                aria-hidden="true"
              />
              {model.done ? 'Đã hoàn tất' : 'Các tác tử đang làm việc'}
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

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
        <Stage agents={model.agents} snapshots={model.snapshots} last={last} elapsed={elapsed} live={live && !model.done} />
        <Feed steps={visible} live={live && !model.done} />
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

function Stage({
  agents,
  snapshots,
  last,
  elapsed,
  live
}: {
  agents: StageAgentId[];
  snapshots: ReturnType<typeof deriveStage>['snapshots'];
  last?: TraceStep;
  elapsed: number;
  live: boolean;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  useLayoutEffect(() => {
    const el = boxRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(([entry]) => setSize({ w: entry.contentRect.width, h: entry.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const pos = layout(agents);
  const ends = last ? stepEndpoints(last) : null;
  const half = (id: StageAgentId) => (id === 'orchestrator' ? 106 : 94) + 8;
  const cx = (id: StageAgentId) =>
    Math.min(Math.max((pos[id]?.x ?? 0.5) * size.w, half(id)), Math.max(size.w - half(id), half(id)));
  const px = (id: StageAgentId) => ({ x: cx(id), y: (pos[id]?.y ?? 0.5) * size.h });

  return (
    <div className="border-b border-border-subtle p-4 sm:p-6 lg:border-b-0 lg:border-r">
      {/* Hub-and-spoke stage on wide screens (hand-offs travel along the links); a plain list on phones. */}
      <div ref={boxRef} className="relative grid gap-2 md:block md:h-[400px]">
        <svg className="absolute inset-0 hidden size-full md:block" aria-hidden="true">
          {agents
            .filter((a) => a !== 'orchestrator')
            .map((a) => {
              const p = px(a);
              const c = px('orchestrator');
              const hot = Boolean(ends && ends.includes(a));
              return (
                <line
                  key={a}
                  x1={c.x}
                  y1={c.y}
                  x2={p.x}
                  y2={p.y}
                  stroke={hot ? 'var(--accent)' : 'var(--border-default)'}
                  strokeWidth={hot ? 2 : 1}
                  strokeDasharray={hot ? undefined : '3 5'}
                />
              );
            })}
        </svg>
        {ends && size.w > 0 && live && (
          <div className="hidden md:block">
            <Packet key={last!.step_id} from={px(ends[0])} to={px(ends[1])} label={packetLabel(last!)} />
          </div>
        )}
        {agents.map((a) => (
          <div
            key={a}
            className="md:absolute md:-translate-x-1/2 md:-translate-y-1/2"
            style={size.w > 0 ? { left: `${cx(a)}px`, top: `${(pos[a]?.y ?? 0.5) * 100}%` } : undefined}
          >
            <AgentNode id={a} snap={snapshots[a]} elapsed={elapsed} />
          </div>
        ))}
      </div>
    </div>
  );
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

function Packet({ from, to, label }: { from: { x: number; y: number }; to: { x: number; y: number }; label: string }) {
  const style = {
    '--fx': `${from.x}px`,
    '--fy': `${from.y}px`,
    '--tx': `${to.x}px`,
    '--ty': `${to.y}px`
  } as React.CSSProperties;
  return (
    <div className="agent-packet pointer-events-none absolute left-0 top-0 z-10" style={style} aria-hidden="true">
      <span className="flex -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 whitespace-nowrap rounded-full bg-ink px-2.5 py-1 text-[11px] font-semibold text-ink-inverse shadow-[0_6px_14px_-6px_rgba(0,0,0,0.5)]">
        <span className="size-1.5 rounded-full bg-amber" />
        {label}
      </span>
    </div>
  );
}

function AgentNode({
  id,
  snap,
  elapsed
}: {
  id: StageAgentId;
  snap: ReturnType<typeof deriveStage>['snapshots'][StageAgentId];
  elapsed: number;
}) {
  const meta = STAGE_AGENTS[id];
  const Icon = ICONS[id];
  const busy = snap.state === 'busy' || snap.state === 'fixing';
  const hub = id === 'orchestrator';
  const tone =
    snap.state === 'fixing'
      ? 'border-warning'
      : busy
        ? 'border-amber'
        : snap.state === 'done'
          ? 'border-border-default'
          : 'border-border-subtle';
  return (
    <div
      role="region"
      aria-label={meta.ariaName}
      className={`relative rounded-xl border bg-surface-primary p-3 transition-[border-color,opacity] duration-200 ${tone} ${
        snap.state === 'unused' ? 'opacity-50' : ''
      } ${hub ? 'w-full md:w-[212px]' : 'w-full md:w-[188px]'} ${busy ? 'agent-busy' : ''} ${
        hub ? 'shadow-[0_10px_30px_-18px_rgba(29,28,26,0.55)]' : 'shadow-[0_1px_2px_rgba(29,28,26,0.05)]'
      }`}
    >
      <div className="flex items-center gap-2.5">
        <span
          className={`grid size-8 shrink-0 place-items-center rounded-lg ${
            hub ? 'bg-ink text-amber' : busy ? 'bg-amber-soft text-text-accent' : 'bg-surface-secondary text-text-secondary'
          }`}
        >
          <Icon className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="m-0 truncate text-[13px] font-semibold text-text-primary">{meta.name}</p>
          <p className="m-0 flex items-center gap-1.5 text-xs">
            <span
              className={
                snap.state === 'done'
                  ? 'text-text-success'
                  : snap.state === 'fixing'
                    ? 'text-text-warning'
                    : busy
                      ? 'text-text-accent'
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
            <span key={s} className="rounded-md bg-surface-secondary px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-text-primary">
              {s}
            </span>
          ))}
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

function who(id: string | null | undefined): string {
  if (!id) return '';
  return id in STAGE_AGENTS ? STAGE_AGENTS[id as StageAgentId].name : id === 'system' ? 'Hệ thống' : id;
}

function Feed({ steps, live }: { steps: TraceStep[]; live: boolean }) {
  const listRef = useRef<HTMLOListElement>(null);
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [steps.length]);

  return (
    <div className="flex min-h-0 flex-col">
      <div className="flex items-center justify-between px-5 pt-4 pb-2 sm:px-6">
        <h3 className="m-0 text-[13px] font-semibold text-text-primary">Trao đổi giữa các tác tử</h3>
        <span className="text-xs tabular-nums text-text-tertiary">{steps.length} bước</span>
      </div>
      <ol ref={listRef} className="m-0 max-h-[420px] list-none space-y-3 overflow-y-auto px-5 pb-5 sm:px-6" aria-live="polite">
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
