import React, { useEffect, useMemo, useState } from 'react';
import { ArrowRight, RefreshCw } from 'lucide-react';
import type { TraceStep } from '../model/types';

export interface OrchestratorBoardProps {
  steps: TraceStep[];
  query?: string;
  reportId?: string | null;
  isDisconnected?: boolean;
  onOpenReport?: (reportId: string) => void;
  onRetry?: () => void;
  className?: string;
}

type AgentState = 'idle' | 'run' | 'done' | 'fix';

const STATE_LABELS: Record<AgentState, string> = {
  idle: 'Chờ',
  run: 'Đang làm',
  done: 'Xong',
  fix: 'Đang sửa'
};

const STATE_CLASSES: Record<AgentState, { card: string; badge: string }> = {
  idle: {
    card: 'border-line bg-surface-primary',
    badge: 'bg-surface-secondary text-text-muted'
  },
  run: {
    card: 'border-accent bg-surface-primary',
    badge: 'bg-accent/20 text-accent font-semibold'
  },
  done: {
    card: 'border-line bg-surface-primary',
    badge: 'bg-success-soft text-text-success font-medium'
  },
  fix: {
    card: 'border-warning bg-surface-primary',
    badge: 'bg-warning-soft text-text-warning font-semibold'
  }
};

const QUESTION_TYPE_LABELS: Record<string, string> = {
  lookup: 'Tra cứu nhanh',
  company_profile: 'Hồ sơ doanh nghiệp',
  ranking: 'Xếp hạng',
  trend: 'Diễn biến chuỗi thời gian',
  head_to_head: 'Đối đầu',
  sector_theme: 'Chủ đề ngành',
  relationship: 'Mối quan hệ chỉ tiêu'
};

function formatTimer(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export const OrchestratorBoard: React.FC<OrchestratorBoardProps> = ({
  steps,
  query,
  reportId,
  isDisconnected = false,
  onOpenReport,
  onRetry,
  className = ''
}) => {
  const [userInteracted, setUserInteracted] = useState(false);

  // 1. Plan step extraction
  const planStep = steps.find((s) => s.kind === 'plan');
  const planDetail = planStep?.detail as
    | {
        question_type?: string;
        tools?: Array<{ tool: string; agent: string; label: string }>;
        agents?: Array<{ agent: string; decision: string; reason: string }>;
      }
    | undefined;

  // 2. Child agents: ONLY those in plan with decision === 'run'
  // plus 'critic' (Phản biện) if critic appears or is planned
  const childAgents = useMemo(() => {
    const list: Array<{ id: string; label: string; tools: string[] }> = [];

    const plannedAgents = planDetail?.agents || [];
    const hasCriticStep = steps.some((s) => s.actor === 'critic' || s.recipient === 'critic');

    plannedAgents.forEach((a) => {
      // Rule: skip any agent that has decision !== 'run' (e.g. macro with 'skip')
      if (a.decision !== 'run') return;

      const agentTools = (planDetail?.tools || [])
        .filter((t) => t.agent.toLowerCase() === a.agent.toLowerCase())
        .map((t) => t.label || t.tool);

      const label =
        a.agent.toLowerCase() === 'company'
          ? 'Company'
          : a.agent.toLowerCase() === 'sector'
          ? 'Sector'
          : a.agent;

      list.push({
        id: a.agent.toLowerCase(),
        label,
        tools: agentTools
      });
    });

    // Check if critic should be added (if arm has critic or critic participated)
    const alreadyHasCritic = list.some((c) => c.id === 'critic');
    if (!alreadyHasCritic && (hasCriticStep || plannedAgents.some((a) => a.agent.toLowerCase() === 'critic' && a.decision === 'run'))) {
      list.push({
        id: 'critic',
        label: 'Phản biện',
        tools: ['Phản biện chéo và kiểm định']
      });
    }

    return list;
  }, [planDetail, steps]);

  // 3. State derivation for agents
  // Rules:
  // - assign to agent -> "run" (Đang làm)
  // - tool_result or draft from agent -> "done" (Xong)
  // - critique_issue sent to agent -> "fix" (Đang sửa)
  // - revision from agent -> "done" (Xong)
  // - Orchestrator "done" when report_ready
  const agentStates = useMemo(() => {
    const states: Record<string, { state: AgentState; summary: string }> = {
      orchestrator: {
        state: steps.length === 0 ? 'idle' : 'run',
        summary: planStep ? `Dạng câu hỏi: ${QUESTION_TYPE_LABELS[planDetail?.question_type || ''] || planDetail?.question_type || ''}` : 'Nhận câu hỏi'
      }
    };

    childAgents.forEach((ag) => {
      states[ag.id] = {
        state: 'idle',
        summary: ag.tools.length > 0 ? ag.tools.join(' · ') : 'Chờ giao việc'
      };
    });

    for (const step of steps) {
      const actor = step.actor.toLowerCase();
      const recipient = step.recipient?.toLowerCase();

      // Orchestrator
      if (step.kind === 'report_ready') {
        states.orchestrator = {
          state: 'done',
          summary: 'Báo cáo sẵn sàng'
        };
      } else if (step.kind === 'plan') {
        const qLabel = QUESTION_TYPE_LABELS[planDetail?.question_type || ''] || planDetail?.question_type || '';
        states.orchestrator = {
          state: 'run',
          summary: `Dạng câu hỏi: ${qLabel}`
        };
      } else if (actor === 'orchestrator' && step.summary) {
        if (states.orchestrator.state !== 'done') {
          states.orchestrator.summary = step.summary;
        }
      }

      // Child agents
      if (step.kind === 'assign' && recipient && states[recipient]) {
        states[recipient] = {
          state: 'run',
          summary: step.summary || 'Đang thực hiện phân tích'
        };
      } else if ((step.kind === 'tool_result' || step.kind === 'draft') && states[actor]) {
        states[actor] = {
          state: 'done',
          summary: step.summary || 'Hoàn thành tính toán'
        };
      } else if (step.kind === 'critique_issue') {
        if (recipient && states[recipient]) {
          states[recipient] = {
            state: 'fix',
            summary: step.summary || 'Đang sửa theo phản biện'
          };
        }
        if (states.critic) {
          states.critic = {
            state: 'run',
            summary: step.summary || 'Kiểm tra chéo'
          };
        }
      } else if (step.kind === 'revision') {
        if (states[actor]) {
          states[actor] = {
            state: 'done',
            summary: step.summary || 'Đã sửa theo phản biện'
          };
        }
      } else if (step.kind === 'accept' && states.critic) {
        states.critic = {
          state: 'done',
          summary: step.summary || 'Phê duyệt báo cáo'
        };
      }
    }

    // When report is ready, all active agents are done
    const isCompleted = steps.some((s) => s.kind === 'report_ready');
    if (isCompleted) {
      states.orchestrator = {
        state: 'done',
        summary: 'Báo cáo sẵn sàng'
      };
      childAgents.forEach((ag) => {
        states[ag.id] = {
          state: 'done',
          summary: states[ag.id]?.summary || 'Hoàn tất'
        };
      });
    }

    return states;
  }, [steps, childAgents, planStep, planDetail]);

  // 4. Elapsed time
  const lastMs = steps.length > 0 ? steps[steps.length - 1].t_ms : 0;
  const timeDisplay = formatTimer(lastMs);

  // 5. Check if report is ready
  const isReportReady = Boolean(reportId || steps.some((s) => s.kind === 'report_ready'));
  const effectiveReportId =
    reportId ||
    (steps.find((s) => s.kind === 'report_ready')?.detail?.report_id as string | undefined);

  // Auto-redirect to report after 1.5s if not interacted and not prefers-reduced-motion
  useEffect(() => {
    if (!isReportReady || !effectiveReportId || userInteracted || !onOpenReport) return;

    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const timer = setTimeout(() => {
      onOpenReport(effectiveReportId);
    }, prefersReducedMotion ? 0 : 1500);

    return () => clearTimeout(timer);
  }, [isReportReady, effectiveReportId, userInteracted, onOpenReport]);

  const orState = agentStates.orchestrator || { state: 'idle', summary: '' };
  const orClass = STATE_CLASSES[orState.state];

  return (
    <div className={`bg-surface-secondary border border-line rounded-lg p-5 ${className}`}>
      {/* Top row: query and elapsed time */}
      <div className="flex justify-between items-baseline gap-2 mb-3">
        <span className="text-sm font-medium text-text-primary truncate">
          {query || 'Phiên phân tích'}
        </span>
        <span className="font-mono text-xs text-text-muted">{timeDisplay}</span>
      </div>

      {/* Top card: Orchestrator */}
      <div
        className={`border rounded p-3 transition-colors ${orClass.card}`}
        role="region"
        aria-label="Điều phối viên"
      >
        <div className="flex justify-between items-center text-xs font-semibold text-text-primary">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-text-secondary" aria-hidden="true" />
            Điều phối viên
          </span>
          <span className={`px-2 py-0.5 rounded text-[11px] ${orClass.badge}`}>
            {STATE_LABELS[orState.state]}
          </span>
        </div>
        <div className="text-xs text-text-secondary mt-1 min-h-[18px]">
          {orState.summary}
        </div>
      </div>

      {/* SVG Connector Line */}
      {childAgents.length > 0 && (
        <svg
          viewBox="0 0 300 22"
          preserveAspectRatio="none"
          width="100%"
          height="22"
          aria-hidden="true"
          className="overflow-visible my-0.5"
        >
          {childAgents.length === 1 && (
            <path
              d="M150 0V22"
              fill="none"
              stroke="var(--border-strong, #c9c8c0)"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          )}
          {childAgents.length === 2 && (
            <path
              d="M150 0V11 M75 11H225 M75 11V22 M225 11V22"
              fill="none"
              stroke="var(--border-strong, #c9c8c0)"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          )}
          {childAgents.length >= 3 && (
            <path
              d="M150 0V11 M50 11H250 M50 11V22 M150 11V22 M250 11V22"
              fill="none"
              stroke="var(--border-strong, #c9c8c0)"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>
      )}

      {/* Child agent cards */}
      {childAgents.length > 0 && (
        <div
          className={`grid gap-2 ${
            childAgents.length === 1
              ? 'grid-cols-1'
              : childAgents.length === 2
              ? 'grid-cols-1 sm:grid-cols-2'
              : 'grid-cols-1 sm:grid-cols-3'
          }`}
        >
          {childAgents.map((ag) => {
            const cur = agentStates[ag.id] || { state: 'idle', summary: '' };
            const cls = STATE_CLASSES[cur.state];

            return (
              <div
                key={ag.id}
                className={`border rounded p-2.5 transition-colors ${cls.card}`}
                role="region"
                aria-label={ag.label}
              >
                <div className="flex justify-between items-center text-xs font-semibold text-text-primary">
                  <span>{ag.label}</span>
                  <span className={`px-2 py-0.5 rounded text-[11px] ${cls.badge}`}>
                    {STATE_LABELS[cur.state]}
                  </span>
                </div>
                <div className="text-[11px] text-text-secondary mt-1 min-h-[16px] leading-tight">
                  {cur.summary}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Disconnection Warning */}
      {isDisconnected && (
        <div className="mt-4 p-3 bg-warning-soft/40 border border-warning/40 rounded flex items-center justify-between text-xs text-text-warning">
          <span>Mất kết nối. Thử lại</span>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1 px-2.5 py-1 bg-surface-primary border border-border-strong rounded font-semibold text-text-primary hover:bg-surface-tertiary"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Thử lại</span>
            </button>
          )}
        </div>
      )}

      {/* Report Ready Action Button */}
      {isReportReady && effectiveReportId && (
        <div className="mt-4 flex items-center justify-end">
          <button
            type="button"
            onClick={() => {
              setUserInteracted(true);
              onOpenReport?.(effectiveReportId);
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-fill-primary text-on-primary font-semibold text-sm rounded shadow-sm hover:opacity-90 transition-opacity"
          >
            <span>Mở báo cáo</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};
