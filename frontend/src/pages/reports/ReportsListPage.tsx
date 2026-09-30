import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, FileSearch, Plus, RotateCw, Search } from 'lucide-react';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import { PageCrumbs, StatusPill } from '@/components/layout/PageCrumbs';
import { getApiBaseUrl } from '@/shared/lib/apiUrl';

/** Mirrors `AnalysisRunSummary` in contracts/openapi.json. */
interface RunSummary {
  run_id: string;
  created_at: string;
  query: string;
  target_ticker?: string | null;
  peer_tickers?: string[];
  period?: string | null;
  status: string;
  latency_ms?: number | null;
  duration_ms?: number | null;
  error_code?: string | null;
  question_type?: string | null;
}

const TYPE_LABELS: Record<string, string> = {
  lookup: 'Tra cứu',
  company_profile: 'Hồ sơ doanh nghiệp',
  ranking: 'Xếp hạng',
  trend: 'Xu hướng',
  head_to_head: 'So sánh',
  sector_theme: 'Toàn ngành',
  relationship: 'Tương quan'
};

type Filter = 'all' | 'answered' | 'blocked';

function statusTone(status: string): { tone: 'ready' | 'warning' | 'neutral'; label: string; answered: boolean } {
  switch (status.toLowerCase()) {
    case 'completed':
    case 'accepted':
    case 'success':
      return { tone: 'ready', label: 'Đã kiểm định', answered: true };
    case 'accepted_with_limitations':
    case 'partial':
      return { tone: 'warning', label: 'Có giới hạn', answered: true };
    case 'blocked':
    case 'error':
    case 'rejected':
      return { tone: 'neutral', label: 'Bị từ chối', answered: false };
    default:
      return { tone: 'neutral', label: status, answered: false };
  }
}

function formatPeriod(period?: string | null): string {
  if (!period) return '';
  const m = /^(\d{4})_Q([1-4])$/.exec(period);
  return m ? `Quý ${m[2]}/${m[1]}` : period;
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).format(d);
}

async function fetchRuns(): Promise<RunSummary[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/runs?limit=100`, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = (await res.json()) as unknown;
  return Array.isArray(data) ? (data as RunSummary[]) : [];
}

export function ReportsListPage() {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<Filter>('all');
  const runsQuery = useQuery({ queryKey: ['runs', 'library'], queryFn: fetchRuns, staleTime: 15_000 });
  const runs = useMemo(() => runsQuery.data ?? [], [runsQuery.data]);

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return runs
      .filter((r) => {
        const answered = statusTone(r.status).answered;
        if (filter === 'answered' && !answered) return false;
        if (filter === 'blocked' && answered) return false;
        if (!q) return true;
        const hay = [r.query, r.target_ticker, ...(r.peer_tickers || [])].join(' ').toLowerCase();
        return hay.includes(q);
      })
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
  }, [runs, search, filter]);

  const counts = useMemo(
    () => ({
      all: runs.length,
      answered: runs.filter((r) => statusTone(r.status).answered).length,
      blocked: runs.filter((r) => !statusTone(r.status).answered).length
    }),
    [runs]
  );

  return (
    <WorkspaceShell activeSection="reports" context={<PageCrumbs items={[{ label: 'Thư viện báo cáo' }]} />}>
      <div className="mx-auto w-full max-w-[1040px] px-4 py-8 sm:px-8 sm:py-10">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="font-display m-0 text-[34px] font-bold leading-tight text-ink">Thư viện báo cáo</h1>
            <p className="mt-2 mb-0 max-w-[60ch] text-[15px] leading-relaxed text-ink-secondary">
              Mọi lượt phân tích đều được lưu lại, kể cả lượt bị từ chối. Mở lại một báo cáo để xem số liệu, nguồn và quá
              trình các tác tử đã làm.
            </p>
          </div>
          <Link
            to="/analysis"
            className="inline-flex h-10 shrink-0 items-center gap-2 self-start rounded-lg bg-ink px-4 text-sm font-semibold text-ink-inverse transition-colors hover:bg-[#3a3a36] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus focus-visible:ring-offset-2 sm:self-auto"
          >
            <Plus className="size-4" aria-hidden="true" />
            Phân tích mới
          </Link>
        </div>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div role="tablist" aria-label="Lọc theo kết quả" className="inline-flex rounded-lg bg-surface-tertiary p-1">
            {(
              [
                ['all', 'Tất cả'],
                ['answered', 'Có báo cáo'],
                ['blocked', 'Bị từ chối']
              ] as Array<[Filter, string]>
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={filter === key}
                onClick={() => setFilter(key)}
                className={`rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus ${
                  filter === key ? 'bg-surface-primary text-ink shadow-[0_1px_2px_rgba(32,32,30,0.1)]' : 'text-ink-secondary hover:text-ink'
                }`}
              >
                {label}
                <span className="ml-1.5 tabular-nums text-ink-tertiary">{counts[key]}</span>
              </button>
            ))}
          </div>
          <label className="relative block w-full sm:w-72">
            <span className="sr-only">Tìm báo cáo</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-tertiary" aria-hidden="true" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm theo câu hỏi hoặc mã ngân hàng"
              className="h-10 w-full rounded-lg border border-border-default bg-surface-primary pl-9 pr-3 text-sm text-ink placeholder:text-ink-tertiary focus:border-border-focus focus:outline-none focus:ring-2 focus:ring-amber-soft"
            />
          </label>
        </div>

        <div className="mt-4 overflow-hidden rounded-xl border border-border-subtle bg-surface-primary shadow-[0_1px_2px_rgba(32,32,30,0.04)]">
          {runsQuery.isLoading ? (
            <ul className="m-0 list-none divide-y divide-border-subtle p-0" aria-busy="true" aria-label="Đang tải">
              {Array.from({ length: 4 }).map((_, i) => (
                <li key={i} className="px-5 py-4">
                  <div className="h-4 w-2/3 animate-pulse rounded bg-surface-tertiary" />
                  <div className="mt-2 h-3 w-1/3 animate-pulse rounded bg-surface-secondary" />
                </li>
              ))}
            </ul>
          ) : runsQuery.isError ? (
            <div className="px-6 py-12 text-center">
              <p className="m-0 text-[15px] font-semibold text-ink">Không tải được danh sách báo cáo</p>
              <p className="mt-1 mb-4 text-sm text-ink-secondary">Máy chủ phân tích có thể đang khởi động lại. Thử lại sau vài giây.</p>
              <button
                type="button"
                onClick={() => void runsQuery.refetch()}
                className="inline-flex items-center gap-2 rounded-lg border border-border-default px-3 py-2 text-sm font-medium text-ink hover:bg-surface-hover"
              >
                <RotateCw className="size-4" aria-hidden="true" />
                Thử lại
              </button>
            </div>
          ) : visible.length === 0 ? (
            <div className="px-6 py-14 text-center">
              <FileSearch className="mx-auto size-8 text-ink-tertiary" aria-hidden="true" />
              <p className="mt-3 mb-1 text-[15px] font-semibold text-ink">
                {runs.length === 0 ? 'Chưa có báo cáo nào' : 'Không có báo cáo khớp bộ lọc'}
              </p>
              <p className="m-0 text-sm text-ink-secondary">
                {runs.length === 0
                  ? 'Đặt một câu hỏi ở mục Phân tích mới; báo cáo sẽ xuất hiện ở đây.'
                  : 'Thử bỏ bớt từ khóa hoặc chọn “Tất cả”.'}
              </p>
            </div>
          ) : (
            <ul className="m-0 list-none divide-y divide-border-subtle p-0">
              {visible.map((run) => {
                const st = statusTone(run.status);
                const tickers = [run.target_ticker, ...(run.peer_tickers || [])].filter(Boolean) as string[];
                const seconds = Math.round(((run.duration_ms ?? run.latency_ms) || 0) / 1000);
                const meta = [
                  run.question_type ? TYPE_LABELS[run.question_type] || run.question_type : null,
                  formatPeriod(run.period),
                  seconds > 0 ? `${seconds} giây` : null,
                  formatWhen(run.created_at)
                ].filter(Boolean);
                return (
                  <li key={run.run_id}>
                    <Link
                      to={`/reports/${run.run_id}`}
                      className="group flex items-center gap-4 px-5 py-4 no-underline transition-colors hover:bg-surface-secondary focus-visible:bg-surface-secondary focus-visible:outline-none"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="m-0 truncate text-[15px] font-medium text-ink">{run.query}</p>
                        <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-ink-secondary">
                          {tickers.map((t) => (
                            <span key={t} className="rounded border border-border-default px-1.5 py-px font-mono text-[11px] font-semibold tracking-wide text-ink">
                              {t}
                            </span>
                          ))}
                          <span>{meta.join(' · ')}</span>
                        </div>
                      </div>
                      <StatusPill tone={st.tone}>{st.label}</StatusPill>
                      <ChevronRight className="size-4 shrink-0 text-ink-tertiary transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </WorkspaceShell>
  );
}

export default ReportsListPage;
