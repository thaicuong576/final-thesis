import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { ArrowUpRight, History } from 'lucide-react';
import { getApiBaseUrl } from '../../analysis-session/useAnalysisSessionStream';

export interface AnalysisRunItem {
  run_id: string;
  created_at: string;
  query: string;
  target_ticker: string;
  peer_tickers: string[];
  period: string;
  status: string;
  latency_ms?: number;
  model_used?: string;
}

export function RecentReportsSummary() {
  const [runs, setRuns] = useState<AnalysisRunItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchRuns = async () => {
      try {
        const baseUrl = getApiBaseUrl();
        const origin =
          typeof window !== 'undefined' && window.location?.origin && window.location.origin !== 'null'
            ? window.location.origin
            : '';
        const endpoint = baseUrl
          ? `${baseUrl}/api/runs?limit=5`
          : origin
          ? `${origin}/api/runs?limit=5`
          : '/api/runs?limit=5';
        const response = await fetch(endpoint, {
          headers: { Accept: 'application/json' }
        });
        if (response.ok) {
          const data = (await response.json()) as AnalysisRunItem[];
          if (isMounted && Array.isArray(data)) {
            setRuns(data);
          }
        }
      } catch {
        // Silently ignore network or environment failures for recent runs widget
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    void fetchRuns();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-ink-secondary flex items-center gap-1.5">
          <History className="w-3.5 h-3.5 text-ink-secondary" />
          <span>Gần đây (SQLite)</span>
        </h3>
        <Link
          to="/reports"
          className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-border hover:text-amber-active underline underline-offset-2"
        >
          <span>Xem tất cả</span>
          <ArrowUpRight className="w-3 h-3" />
        </Link>
      </div>

      <div className="border border-line bg-card rounded-md divide-y divide-border-subtle overflow-hidden">
        {isLoading ? (
          <div className="p-4 space-y-3">
            <div className="animate-pulse space-y-2">
              <div className="h-3.5 bg-surface-tertiary rounded w-2/3" />
              <div className="h-2.5 bg-surface-tertiary rounded w-1/3" />
            </div>
            <div className="animate-pulse space-y-2 pt-2 border-t border-line/40">
              <div className="h-3.5 bg-surface-tertiary rounded w-1/2" />
              <div className="h-2.5 bg-surface-tertiary rounded w-1/4" />
            </div>
          </div>
        ) : runs.length === 0 ? (
          <div className="p-4 text-center text-xs text-ink-secondary bg-surface-secondary/40">
            <p className="font-semibold text-ink">Chưa có phiên phân tích nào được lưu trữ</p>
            <p className="text-[11px] text-ink-tertiary mt-0.5">
              Nhập câu hỏi ở khung phía trên để bắt đầu phân tích và lưu kết quả vào cơ sở dữ liệu.
            </p>
          </div>
        ) : (
          runs.map((run) => {
            const scope = [run.target_ticker, ...(run.peer_tickers || []), run.period]
              .filter(Boolean)
              .join(' · ');
            const dateStr = run.created_at
              ? new Date(run.created_at).toLocaleDateString('vi-VN', {
                  day: '2-digit',
                  month: '2-digit',
                  year: 'numeric'
                })
              : '';

            return (
              <div
                key={run.run_id}
                className="p-3 hover:bg-surface-hover transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs group"
              >
                {/* Col 1 & 2: Report Title & Scope */}
                <div className="min-w-0 flex-1 space-y-0.5">
                  <Link
                    to={`/reports/${run.run_id}`}
                    className="font-semibold text-ink truncate group-hover:text-amber-border transition-colors block"
                  >
                    {run.query}
                  </Link>
                  <div className="text-[11px] font-mono text-ink-secondary truncate">
                    {scope}
                  </div>
                </div>

                {/* Col 3 & 4: Date & Status & Action */}
                <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0 pt-1 sm:pt-0 border-t sm:border-t-0 border-border-subtle/50">
                  <span className="text-[11px] font-mono text-ink-tertiary">
                    {dateStr}
                  </span>
                  <Badge
                    variant="outline"
                    className="bg-[#e4f4ea] text-[#2f9e62] border-[#2f9e62]/30 text-[10px] font-semibold px-2 py-0"
                  >
                    {run.status === 'completed' ? 'Hoàn tất' : run.status}
                  </Badge>
                  <Link
                    to={`/reports/${run.run_id}`}
                    className="text-[11px] font-medium text-ink-secondary hover:text-ink hover:underline shrink-0"
                  >
                    Mở lại
                  </Link>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
