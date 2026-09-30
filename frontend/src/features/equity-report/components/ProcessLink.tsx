import React, { useEffect, useState } from 'react';
import { useEquityReport } from './useEquityReport';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { ProcessTrace } from '@/features/analysis-session';
import type { TraceStep } from '@/features/analysis-session/model/types';
import { getApiBaseUrl } from '@/shared/lib/apiUrl';
import { ListTree } from 'lucide-react';

export const ProcessLink: React.FC<{ onClick?: () => void }> = ({ onClick }) => {
  const { report } = useEquityReport();
  const [open, setOpen] = useState(false);
  const reportId = report.report_id || (report as { run_id?: string }).run_id;

  const [traceState, setTraceState] = useState<{
    isLoading: boolean;
    error: boolean;
    steps: TraceStep[] | null;
    meta: { agents: number; rounds: number; duration: number } | null;
  }>({
    isLoading: Boolean(reportId),
    error: !reportId,
    steps: null,
    meta: null
  });

  useEffect(() => {
    if (!reportId) {
      return;
    }

    let isMounted = true;

    const fetchTrace = async () => {
      try {
        const base =
          getApiBaseUrl() ||
          (typeof window !== 'undefined' && window.location?.origin && window.location.origin !== 'null'
            ? window.location.origin
            : '');
        const res = await fetch(`${base}/api/runs/${reportId}/trace`, {
          headers: { Accept: 'application/json' }
        });

        if (!res.ok) {
          if (isMounted) setTraceState({ isLoading: false, error: true, steps: null, meta: null });
          return;
        }

        const data = (await res.json()) as { steps?: TraceStep[]; duration_ms?: number };
        const steps = (data.steps || []) as TraceStep[];
        if (steps.length === 0) {
          if (isMounted) setTraceState({ isLoading: false, error: false, steps: [], meta: null });
          return;
        }

        // 1. Calculate active agents
        const plan = steps.find((s) => s.kind === 'plan');
        const planned = (plan?.detail?.agents as Array<{ agent: string; decision: string }>) || [];
        const activePlanned = planned.filter((a) => a.decision === 'run').map((a) => a.agent.toLowerCase());
        const set = new Set(activePlanned);
        steps.forEach((s) => {
          if (['company', 'sector', 'macro', 'critic'].includes(s.actor.toLowerCase())) {
            set.add(s.actor.toLowerCase());
          }
        });
        const agents = Math.max(set.size, 1);

        // 2. Calculate critique rounds
        let rounds = 0;
        steps.forEach((s) => {
          const r = Number(s.detail?.round);
          if (!isNaN(r) && r > rounds) rounds = r;
        });

        // 3. Duration
        const lastStep = steps[steps.length - 1];
        const duration = lastStep
          ? Math.round(lastStep.t_ms / 1000)
          : data.duration_ms
          ? Math.round(data.duration_ms / 1000)
          : 0;

        if (isMounted) {
          setTraceState({
            isLoading: false,
            error: false,
            steps,
            meta: { agents, rounds, duration }
          });
        }
      } catch {
        if (isMounted) setTraceState({ isLoading: false, error: true, steps: null, meta: null });
      }
    };

    void fetchTrace();
    return () => {
      isMounted = false;
    };
  }, [reportId]);

  const label = traceState.meta
    ? `Xem quá trình phân tích · ${traceState.meta.agents} agent · ${traceState.meta.rounds} vòng phản biện · ${traceState.meta.duration} giây`
    : 'Xem quá trình phân tích';

  const handleClick = () => {
    setOpen(true);
    onClick?.();
  };

  return (
    <>
      <div className="mt-8 mb-2 print:hidden">
        <button
          type="button"
          onClick={handleClick}
          className="inline-flex items-center gap-2 rounded-md border border-border-default bg-surface-primary px-3 py-2 text-[13px] font-medium text-text-primary transition-colors hover:bg-surface-hover hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus cursor-pointer"
        >
          <ListTree className="size-4 text-text-accent" aria-hidden="true" />
          <span>{label}</span>
        </button>
      </div>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full sm:max-w-2xl p-0 overflow-hidden flex flex-col bg-surface-primary">
          <SheetHeader className="p-4 border-b border-line">
            <SheetTitle className="text-base font-bold text-text-primary">
              Quá trình phân tích
            </SheetTitle>
          </SheetHeader>
          <div className="flex-1 overflow-y-auto p-4 sm:p-6">
            {traceState.isLoading ? (
              <div className="text-center py-12 text-sm text-text-muted">
                Đang tải dữ liệu quá trình phân tích...
              </div>
            ) : traceState.error || !traceState.steps || traceState.steps.length === 0 ? (
              <div className="text-center py-12 text-sm text-text-muted" role="status">
                Chưa có dữ liệu quá trình cho báo cáo này.
              </div>
            ) : (
              <ProcessTrace steps={traceState.steps} live={false} />
            )}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
};
