import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import {
  ArrowDown,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  FileText,
  RotateCcw
} from 'lucide-react';
import type { TraceStep } from '../model/types';
import type { LiveWorkState } from '../useTraceStream';
import {
  QUESTION_TYPES,
  PHASES,
  type StageAgentId,
  type LiveWorkStateInput
} from '../model/agentStage';
import {
  deriveTimeline,
  formatClock
} from '../model/timeline';

export interface ReasoningTimelineProps {
  steps: TraceStep[];
  query?: string;
  live?: boolean;
  reportId?: string | null;
  isDisconnected?: boolean;
  liveWorkState?: LiveWorkState | LiveWorkStateInput;
  onOpenReport?: (reportId: string) => void;
  onRetry?: () => void;
  autoRedirect?: boolean;
  onSelectQuery?: (query: string) => void;
}

const AGENT_COLORS: Record<StageAgentId | 'system', { bg: string; text: string; dot: string; border: string }> = {
  orchestrator: { bg: 'bg-[#7c3aed]/10', text: 'text-[#7c3aed]', dot: 'bg-[#7c3aed]', border: 'border-[#7c3aed]/30' },
  company: { bg: 'bg-[#2563eb]/10', text: 'text-[#2563eb]', dot: 'bg-[#2563eb]', border: 'border-[#2563eb]/30' },
  sector: { bg: 'bg-[#0d9488]/10', text: 'text-[#0d9488]', dot: 'bg-[#0d9488]', border: 'border-[#0d9488]/30' },
  macro: { bg: 'bg-[#d97706]/10', text: 'text-[#d97706]', dot: 'bg-[#d97706]', border: 'border-[#d97706]/30' },
  verifier: { bg: 'bg-[#059669]/10', text: 'text-[#059669]', dot: 'bg-[#059669]', border: 'border-[#059669]/30' },
  critic: { bg: 'bg-[#e11d48]/10', text: 'text-[#e11d48]', dot: 'bg-[#e11d48]', border: 'border-[#e11d48]/30' },
  system: { bg: 'bg-surface-tertiary', text: 'text-text-secondary', dot: 'bg-text-tertiary', border: 'border-border-default' }
};

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return true;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export const ReasoningTimeline: React.FC<ReasoningTimelineProps> = ({
  steps,
  query,
  live = false,
  reportId,
  isDisconnected = false,
  liveWorkState,
  onOpenReport,
  onRetry,
  onSelectQuery
}) => {
  const [filterAgent, setFilterAgent] = useState<StageAgentId | null>(null);
  const [openDetails, setOpenDetails] = useState<Record<string, boolean>>({});
  const [tickMs, setTickMs] = useState(0);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const containerRef = useRef<HTMLDivElement>(null);
  const timelineEndRef = useRef<HTMLDivElement>(null);

  // Check terminal state from steps
  const isCompleteEarly = steps.some((s) => s.kind === 'report_ready') || Boolean(reportId);

  // Live timer tick
  useEffect(() => {
    if (!live || isCompleteEarly || isDisconnected) return;
    const id = setInterval(() => setTickMs((t) => t + 1000), 1000);
    return () => clearInterval(id);
  }, [live, isCompleteEarly, isDisconnected]);

  const lastStepMs = steps.length > 0 ? steps[steps.length - 1].t_ms : 0;
  const elapsedMs =
    isCompleteEarly || (!live && !isDisconnected)
      ? lastStepMs
      : Math.max(lastStepMs, tickMs);

  const timelineData = useMemo(() => {
    return deriveTimeline(steps, liveWorkState, {
      elapsedMs,
      isStreaming: live,
      isDisconnected,
      reportId
    });
  }, [steps, liveWorkState, elapsedMs, live, isDisconnected, reportId]);

  const { entries, liveTail, participatingAgents, isComplete, isBlocked } = timelineData;

  // Filter entries if agent chip is clicked
  const visibleEntries = useMemo(() => {
    if (!filterAgent) return entries;
    return entries.filter((e) => e.agentId === filterAgent || e.kind === 'complete' || e.kind === 'blocked');
  }, [entries, filterAgent]);

  // Derive phase index (0 to 5)
  const currentPhaseIndex = useMemo(() => {
    if (isComplete) return 5;
    if (isBlocked) return 0;
    if (steps.some((s) => s.kind === 'accept' || s.kind === 'critique_issue' || s.kind === 'revision')) return 4;
    if (steps.some((s) => s.kind === 'verify')) return 3;
    if (steps.some((s) => s.kind === 'draft' || s.kind === 'compose') || liveWorkState?.activeWriterRole) return 2;
    if (steps.some((s) => s.kind === 'tool_result') || (liveWorkState?.toolCallsByRole && Object.keys(liveWorkState.toolCallsByRole).length > 0)) return 1;
    return 0;
  }, [isComplete, isBlocked, steps, liveWorkState]);

  // Auto-scroll when near bottom
  useEffect(() => {
    if (isAtBottom && timelineEndRef.current && live) {
      const behavior = prefersReducedMotion() ? 'auto' : 'smooth';
      if (typeof timelineEndRef.current.scrollIntoView === 'function') {
        timelineEndRef.current.scrollIntoView({ behavior, block: 'nearest' });
      }
    }
  }, [entries.length, liveTail, isAtBottom, live]);

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const atBottom = scrollHeight - scrollTop - clientHeight < 80;
    setIsAtBottom(atBottom);
  }, []);

  const scrollToBottom = useCallback(() => {
    setIsAtBottom(true);
    const behavior = prefersReducedMotion() ? 'auto' : 'smooth';
    if (typeof timelineEndRef.current?.scrollIntoView === 'function') {
      timelineEndRef.current.scrollIntoView({ behavior, block: 'nearest' });
    }
  }, []);

  const toggleDetail = useCallback((id: string) => {
    setOpenDetails((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  // Question type determination
  const questionTypeKey = useMemo(() => {
    const planStep = steps.find((s) => s.kind === 'plan');
    return (planStep?.detail?.question_type as string) || liveWorkState?.planSummary?.questionType || '';
  }, [steps, liveWorkState]);

  const questionTypeLabel = questionTypeKey && QUESTION_TYPES[questionTypeKey] ? QUESTION_TYPES[questionTypeKey] : 'Phân tích tài chính';

  // Effective reportId
  const effectiveReportId = reportId || timelineData.reportId || (steps.find((s) => s.kind === 'report_ready')?.detail?.report_id as string | undefined);

  return (
    <section className="overflow-hidden rounded-2xl border border-border-subtle bg-surface-primary shadow-[0_1px_2px_rgba(29,28,26,0.04),0_20px_44px_-28px_rgba(60,45,20,0.35)]">
      {/* 1. Header (Spec item 7) */}
      <header className="border-b border-border-subtle px-5 pt-5 pb-4 sm:px-7">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="m-0 flex flex-wrap items-center gap-2 text-[13px] text-text-secondary">
              <span
                aria-hidden="true"
                className={`size-2 rounded-full ${
                  isDisconnected
                    ? 'bg-danger'
                    : isBlocked
                      ? 'bg-warning'
                      : isComplete
                        ? 'bg-success'
                        : 'bg-amber agent-live-dot'
                }`}
              />
              <span className="font-medium text-text-primary">
                {isDisconnected
                  ? 'Mất kết nối'
                  : isBlocked
                    ? 'Từ chối'
                    : isComplete
                      ? 'Đã hoàn tất'
                      : 'Các agent đang làm việc'}
              </span>
              <span className="rounded-md border border-border-default px-1.5 py-px text-xs text-text-secondary">
                {questionTypeLabel}
              </span>

              {isComplete && effectiveReportId && (
                <button
                  type="button"
                  onClick={() => onOpenReport?.(effectiveReportId)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-ink px-3 py-1 text-xs font-semibold text-ink-inverse hover:bg-[#3a3a36] shadow-sm transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ml-2"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Mở báo cáo</span>
                </button>
              )}
            </div>

            <h2 className="font-display mt-2 mb-0 text-[20px] font-bold leading-snug text-balance text-text-primary sm:text-[24px]">
              {query || 'Phiên phân tích'}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            <span
              aria-label="Thời gian đã chạy"
              className="font-mono text-[15px] font-semibold tabular-nums text-text-primary"
            >
              {formatClock(elapsedMs)}
            </span>
          </div>
        </div>

        {/* 6-phase thin progress bar (Spec item 7) */}
        <ol
          aria-label="Tiến độ"
          className="mt-4 mb-0 grid list-none grid-cols-3 gap-1.5 p-0 sm:grid-cols-6"
        >
          {PHASES.map((p, idx) => {
            const isDone = isComplete || idx < currentPhaseIndex;
            const isNow = !isComplete && idx === currentPhaseIndex && !isBlocked;
            return (
              <li key={p} className="min-w-0">
                <div
                  className={`h-1 rounded-full transition-colors ${
                    isDone ? 'bg-text-primary' : isNow ? 'bg-amber agent-phase-now' : 'bg-surface-tertiary'
                  }`}
                />
                <span
                  {...(isNow ? { 'aria-current': 'step' } : {})}
                  className={`mt-1.5 block truncate text-xs ${
                    isNow
                      ? 'font-medium text-text-primary'
                      : isDone
                        ? 'text-text-secondary'
                        : 'text-text-tertiary'
                  }`}
                >
                  {p}
                </span>
              </li>
            );
          })}
        </ol>
      </header>

      {/* Disconnect banner */}
      {isDisconnected && !isComplete && (
        <div className="flex items-center justify-between border-b border-warning/30 bg-warning/10 px-5 py-2.5 sm:px-7 text-xs text-text-warning">
          <span>Mất kết nối. Thử lại</span>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1 font-semibold underline hover:no-underline"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Thử lại</span>
            </button>
          )}
        </div>
      )}

      {/* 2. Compact Agent Chips Row (Spec item 6) */}
      {participatingAgents.length > 0 && (
        <nav
          aria-label="Lọc theo agent"
          className="flex items-center gap-2 border-b border-border-subtle bg-surface-secondary/40 px-5 py-2.5 sm:px-7 overflow-x-auto no-scrollbar"
        >
          <span className="text-xs font-medium text-text-tertiary whitespace-nowrap mr-1">
            Agent:
          </span>
          {participatingAgents.map((agent) => {
            const isSelected = filterAgent === agent.id;
            const colors = AGENT_COLORS[agent.id] || AGENT_COLORS.system;
            return (
              <div
                key={agent.id}
                role="region"
                aria-label={agent.ariaName}
                className="shrink-0"
              >
                <button
                  type="button"
                  onClick={() => setFilterAgent(isSelected ? null : agent.id)}
                  aria-pressed={isSelected}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-all ${
                    isSelected
                      ? `${colors.bg} ${colors.border} ${colors.text} ring-2 ring-accent/40 font-semibold shadow-xs`
                      : 'border-border-default bg-surface-primary text-text-secondary hover:border-border-strong hover:text-text-primary'
                  }`}
                >
                  <span className={`size-1.5 rounded-full ${colors.dot}`} aria-hidden="true" />
                  <span>{agent.name}</span>
                  {agent.countLabel && (
                    <span className="text-[11px] text-text-tertiary opacity-85">
                      ({agent.countLabel})
                    </span>
                  )}
                </button>
              </div>
            );
          })}
          {filterAgent && (
            <button
              type="button"
              onClick={() => setFilterAgent(null)}
              className="text-xs text-text-tertiary hover:text-text-primary underline shrink-0 ml-1"
            >
              Xem tất cả
            </button>
          )}
        </nav>
      )}

      {/* 3. Timeline section ("Dòng suy luận") (Spec items 1, 2, 3, 4, 5, 8, 9, 10, 11) */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        role="log"
        aria-live="polite"
        className="relative max-h-[640px] overflow-y-auto px-4 py-5 sm:px-7"
      >
        <div className="relative">
          {/* Vertical connecting line */}
          <div
            aria-hidden="true"
            className="absolute left-[38px] sm:left-[47px] top-3 bottom-3 w-px bg-border-subtle pointer-events-none"
          />

          <div className="space-y-5">
            {visibleEntries.map((entry) => {
              const colors = AGENT_COLORS[entry.agentId] || AGENT_COLORS.system;
              const isDetailsOpen = Boolean(openDetails[entry.id]);

              return (
                <article
                  key={entry.id}
                  className="relative flex items-start gap-3 sm:gap-4 group text-sm"
                >
                  {/* Left gutter: timestamp (mm:ss) + colored dot */}
                  <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 w-[46px] sm:w-[56px] pt-0.5 select-none">
                    <span className="font-mono text-xs tabular-nums text-text-tertiary font-medium">
                      {entry.formattedTime}
                    </span>
                    <span
                      aria-hidden="true"
                      className={`size-2.5 rounded-full shrink-0 ${colors.dot} ring-4 ring-surface-primary z-10 transition-transform group-hover:scale-110`}
                    />
                  </div>

                  {/* Right content: Agent name + prose narrative */}
                  <div className="flex-1 min-w-0 pb-1">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                      <span className={`font-semibold ${colors.text} text-[13.5px] sm:text-[14px]`}>
                        {entry.agentName}
                      </span>
                    </div>

                    {/* Prose text */}
                    <p className="mt-0.5 text-text-primary text-[13.5px] sm:text-[14px] leading-relaxed">
                      {entry.prose}
                    </p>

                    {/* Collapsible: "Xem kế hoạch" (Spec item 5) */}
                    {entry.kind === 'plan' && entry.planDetail && (
                      <div className="mt-2">
                        <button
                          type="button"
                          onClick={() => toggleDetail(entry.id)}
                          aria-expanded={isDetailsOpen}
                          className="inline-flex items-center gap-1 text-xs font-medium text-text-secondary hover:text-text-primary underline decoration-dotted"
                        >
                          <span>{isDetailsOpen ? 'Thu gọn kế hoạch' : 'Xem kế hoạch'}</span>
                          {isDetailsOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>

                        {isDetailsOpen && (
                          <div className="mt-2 rounded-lg border border-border-subtle bg-surface-secondary/50 p-3 text-xs space-y-1.5 animate-in fade-in duration-150">
                            {entry.planDetail.questionType && (
                              <div>
                                <span className="font-semibold text-text-tertiary">Dạng câu hỏi: </span>
                                <span className="text-text-primary font-medium">
                                  {QUESTION_TYPES[entry.planDetail.questionType] || entry.planDetail.questionType}
                                </span>
                              </div>
                            )}
                            {entry.planDetail.entities && entry.planDetail.entities.length > 0 && (
                              <div>
                                <span className="font-semibold text-text-tertiary">Thực thể: </span>
                                <span className="text-text-primary">{entry.planDetail.entities.join(', ')}</span>
                              </div>
                            )}
                            {entry.planDetail.periods && entry.planDetail.periods.length > 0 && (
                              <div>
                                <span className="font-semibold text-text-tertiary">Kỳ phân tích: </span>
                                <span className="text-text-primary">{entry.planDetail.periods.join(', ')}</span>
                              </div>
                            )}
                            {entry.planDetail.metrics && entry.planDetail.metrics.length > 0 && (
                              <div>
                                <span className="font-semibold text-text-tertiary">Chỉ tiêu: </span>
                                <span className="text-text-primary">{entry.planDetail.metrics.join(', ')}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Collapsible: "Xem số liệu (N)" (Spec item 5) */}
                    {entry.kind === 'data' && entry.facts && entry.facts.length > 0 && (
                      <div className="mt-2">
                        <button
                          type="button"
                          onClick={() => toggleDetail(entry.id)}
                          aria-expanded={isDetailsOpen}
                          className="inline-flex items-center gap-1 text-xs font-medium text-text-secondary hover:text-text-primary underline decoration-dotted"
                        >
                          <span>{isDetailsOpen ? 'Thu gọn số liệu' : `Xem số liệu (${entry.facts.length})`}</span>
                          {isDetailsOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>

                        {isDetailsOpen && (
                          <div className="mt-2 max-h-56 overflow-y-auto rounded-lg border border-border-subtle bg-surface-secondary/50 p-2 text-xs space-y-1 animate-in fade-in duration-150">
                            {entry.facts.map((fact) => (
                              <div
                                key={fact.factId || fact.label}
                                className="flex items-baseline justify-between gap-3 border-b border-border-subtle/50 py-1 last:border-0"
                              >
                                <span className="text-text-secondary flex-1 truncate">{fact.label}</span>
                                <span className="font-mono font-semibold text-text-primary shrink-0">
                                  {fact.displayValue}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Inline Quote Block with Streaming Text & Verdict Annotations (Spec item 2) */}
                    {entry.draftDetail && (
                      <blockquote className="my-2.5 border-l-2 border-border-strong pl-3.5 py-1 text-text-primary bg-surface-secondary/30 rounded-r-md">
                        <div className="text-[13.5px] leading-relaxed space-y-1.5">
                          {entry.draftDetail.verdicts && entry.draftDetail.verdicts.length > 0 ? (
                            entry.draftDetail.verdicts.map((v, vIdx) => {
                              const isKept = v.verdict === 'kept';
                              return (
                                <div key={v.sentence || vIdx} className="space-y-0.5">
                                  <span className={isKept ? 'text-text-primary' : 'line-through text-text-tertiary'}>
                                    {v.sentence}
                                  </span>
                                  {isKept ? (
                                    <span className="inline-flex items-center gap-1 text-[11.5px] text-success font-medium ml-2">
                                      ✓ khớp dữ kiện
                                    </span>
                                  ) : (
                                    <div className="text-[11.5px] text-danger font-medium">
                                      ✗ bị loại: {v.explanationVi || v.dropReason || 'số liệu không khớp'}
                                    </div>
                                  )}
                                </div>
                              );
                            })
                          ) : (
                            <p className="whitespace-pre-wrap">
                              {entry.draftDetail.text}
                              {entry.draftDetail.isStreaming && (
                                <span
                                  aria-hidden="true"
                                  className="inline-block w-1.5 h-4 ml-0.5 bg-accent align-middle animate-pulse agent-typing-cursor"
                                />
                              )}
                            </p>
                          )}
                        </div>
                      </blockquote>
                    )}

                    {/* Terminal Complete Action: Button Mở báo cáo (Spec items 2, 7) */}
                    {entry.kind === 'complete' && effectiveReportId && (
                      <div className="mt-3">
                        <button
                          type="button"
                          onClick={() => onOpenReport?.(effectiveReportId)}
                          className="inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-ink-inverse hover:bg-[#3a3a36] shadow-sm transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                        >
                          <FileText className="w-4 h-4" />
                          <span>Mở báo cáo</span>
                          <ArrowRight className="w-4 h-4" />
                        </button>
                      </div>
                    )}

                    {/* Blocked / Refusal Action with Suggestions (Spec item 8) */}
                    {entry.kind === 'blocked' && entry.blockedDetail?.suggestions && (
                      <div className="mt-3 space-y-1.5">
                        <span className="text-xs font-medium text-text-secondary">
                          Bạn có thể thử các câu hỏi gợi ý:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {entry.blockedDetail.suggestions.map((sug) => (
                            <button
                              key={sug}
                              type="button"
                              onClick={() => onSelectQuery?.(sug)}
                              className="rounded-md border border-border-default bg-surface-primary px-2.5 py-1 text-xs text-text-primary hover:border-accent hover:text-accent transition-colors"
                            >
                              {sug}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </article>
              );
            })}

            {/* 4. Live Tail Item (Spec item 3) */}
            {liveTail && (
              <div className="relative flex items-center gap-3 sm:gap-4 pt-1 text-sm animate-in fade-in duration-150">
                <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 w-[46px] sm:w-[56px] select-none">
                  <span className="font-mono text-xs tabular-nums text-text-tertiary font-medium">
                    {liveTail.formattedTime}
                  </span>
                  <span
                    aria-hidden="true"
                    className="size-2.5 rounded-full shrink-0 bg-amber ring-4 ring-surface-primary agent-live-dot z-10"
                  />
                </div>
                <div className="flex items-center gap-2 text-text-secondary text-xs sm:text-sm">
                  <span className="font-semibold text-text-primary">{liveTail.agentName}:</span>
                  <span className="italic">{liveTail.activity}</span>
                </div>
              </div>
            )}

            <div ref={timelineEndRef} className="h-2" />
          </div>
        </div>
      </div>

      {/* Floating "Xuống mục mới nhất" button (Spec item 4) */}
      {!isAtBottom && live && (
        <div className="absolute bottom-4 right-6 z-20">
          <button
            type="button"
            onClick={scrollToBottom}
            className="inline-flex items-center gap-1.5 rounded-full bg-surface-primary border border-border-default px-3 py-1.5 text-xs font-semibold text-text-primary shadow-md hover:bg-surface-hover transition-all animate-in slide-in-from-bottom-2 duration-150"
          >
            <span>Xuống mục mới nhất</span>
            <ArrowDown className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </section>
  );
};
