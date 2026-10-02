import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, CircleAlert, X } from 'lucide-react';
import { WorkspaceShell } from '../../components/layout/WorkspaceShell';
import { useAnalysisCapabilities } from '../../features/create-analysis/hooks/useAnalysisCapabilities';
import { AnalysisSessionWorkspace } from '../../features/analysis-session/components/AnalysisSessionWorkspace';
import type { TraceStep } from '../../features/analysis-session/model/types';
import { formatCapabilitiesPeriods, mapErrorCodeToMessage } from '../../features/analysis-session/useTraceStream';
import { DEFAULT_METRICS } from '@/features/equity-report';
import { getApiBaseUrl } from '@/shared/lib/apiUrl';
import { formatQuarter } from '@/entities/capability/model/coverage';
import { buildUploadSuggestions } from '@/features/onboarding/uploadSuggestions';

export interface CreateAnalysisPageProps {
  initialMode?: 'ASK' | 'SESSION';
  initialSteps?: TraceStep[];
}

export function CreateAnalysisPage({ initialMode = 'ASK', initialSteps }: CreateAnalysisPageProps = {}) {
  const capabilitiesQuery = useAnalysisCapabilities();
  const capabilities = capabilitiesQuery.data;

  const [searchParams, setSearchParams] = useSearchParams();
  const [mode, setMode] = useState<'ASK' | 'SESSION'>(initialMode);
  const [question, setQuestion] = useState<string>(() => searchParams.get('q') || '');
  const [errorInfo, setErrorInfo] = useState<{ message: string; suggestions?: string[] } | null>(null);
  const fixtureSteps = initialSteps;
  const [isLiveStream, setIsLiveStream] = useState<boolean>(true);

  const uploadId = searchParams.get('upload_id') || searchParams.get('upload');
  const uploadEntity = searchParams.get('entity') || '';
  const uploadPeriodRaw = searchParams.get('period');
  const uploadPeriodDisplay = uploadPeriodRaw ? formatQuarter(uploadPeriodRaw) : '';
  const uploadSuggestions = useMemo(
    () =>
      uploadId ? buildUploadSuggestions(uploadEntity, uploadPeriodRaw, capabilities) : [],
    [uploadId, uploadEntity, uploadPeriodRaw, capabilities]
  );

  const handleClearUpload = () => {
    const next = new URLSearchParams(searchParams);
    next.delete('upload_id');
    next.delete('upload');
    next.delete('entity');
    next.delete('period');
    setSearchParams(next);
  };

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const placeholder =
    capabilities?.suggestedQuestions?.[0] ||
    'Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024';

  const entitiesStr =
    capabilities?.entities && capabilities.entities.length > 0
      ? capabilities.entities.map((e) => e.ticker || e.name || e.id).join(', ')
      : 'ACB, MBB, TCB, VCB, VPB';

  const periodsStr = formatCapabilitiesPeriods(capabilities);

  const metricsStr =
    capabilities?.metrics && capabilities.metrics.length > 0
      ? capabilities.metrics
          .map((m) => {
            const fallback = DEFAULT_METRICS[m.id];
            return m.shortLabel || fallback?.shortLabel || m.acronym || m.label || m.id;
          })
          .slice(0, 4)
          .join(', ')
      : 'Nợ xấu, Bao phủ, ROA, ROE';

  const handleAnalyze = useCallback(() => {
    const trimmed = question.trim();
    if (!trimmed) return;
    setErrorInfo(null);
    const newParams: Record<string, string> = { q: trimmed };
    if (uploadId) newParams.upload_id = uploadId;
    if (searchParams.get('entity')) newParams.entity = searchParams.get('entity')!;
    if (searchParams.get('period')) newParams.period = searchParams.get('period')!;
    setSearchParams(newParams);
    setIsLiveStream(true);
    setMode('SESSION');
  }, [question, uploadId, searchParams, setSearchParams]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAnalyze();
    }
  };

  // Adjust textarea height automatically
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuestion(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.max(72, textareaRef.current.scrollHeight)}px`;
    }
  };

  return (
    <WorkspaceShell activeSection="analysis">
      <div className="min-h-[calc(100vh-56px)] px-4 pb-16 pt-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-[780px]">
          {mode === 'ASK' ? (
            <div className="pt-[6vh] sm:pt-[9vh]">
              <h1 className="font-display m-0 text-[36px] font-bold leading-[1.1] text-balance text-text-primary sm:text-[44px]">
                Bạn muốn phân tích gì?
              </h1>
              <p className="mt-3 mb-0 max-w-[62ch] text-[15px] leading-relaxed text-text-secondary">
                Hỏi bằng tiếng Việt về các ngân hàng niêm yết. Các tác tử chia việc, chương trình tính số liệu, và mỗi
                con số trong báo cáo đều dẫn về trang báo cáo tài chính gốc.
              </p>

              {/* Upload Active Chip */}
              {uploadId && (
                <div className="mt-6 mb-2 inline-flex items-center gap-2 rounded-full border border-amber-border bg-amber-soft px-3 py-1.5 text-xs font-medium text-ink">
                  <span className="size-2 rounded-full bg-amber-500 animate-pulse" aria-hidden="true" />
                  <span>
                    Đang dùng thêm dữ liệu tải lên: <strong>{uploadEntity || 'Ngân hàng mới'}</strong>
                    {uploadPeriodDisplay ? ` (${uploadPeriodDisplay})` : ''}
                  </span>
                  <button
                    type="button"
                    onClick={handleClearUpload}
                    className="ml-1 rounded-full p-0.5 text-ink-secondary hover:bg-amber-border/30 hover:text-ink cursor-pointer"
                    title="Bỏ chọn dữ liệu tải lên"
                    aria-label="Bỏ chọn dữ liệu tải lên"
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
              )}

              <div className="mt-4 rounded-2xl border border-border-default bg-surface-primary shadow-[0_1px_2px_rgba(32,32,30,0.05),0_12px_32px_-16px_rgba(32,32,30,0.18)] transition-[border-color,box-shadow] focus-within:border-border-focus focus-within:shadow-[0_0_0_4px_var(--accent-soft),0_12px_32px_-16px_rgba(32,32,30,0.18)]">
                <textarea
                  ref={textareaRef}
                  value={question}
                  onChange={handleInput}
                  onKeyDown={handleKeyDown}
                  rows={3}
                  placeholder={placeholder}
                  className="block min-h-[88px] w-full resize-none rounded-t-2xl border-none bg-transparent px-5 pt-4 pb-2 text-[17px] leading-relaxed text-text-primary placeholder:text-text-tertiary focus:outline-none"
                  aria-label="Câu hỏi phân tích"
                />
                <div className="flex items-center justify-between gap-3 px-4 pb-3 pt-1">
                  <span className="hidden text-xs text-text-tertiary sm:inline">
                    Enter để gửi · Shift + Enter để xuống dòng
                  </span>
                  <button
                    type="button"
                    onClick={handleAnalyze}
                    disabled={!question.trim()}
                    className="ml-auto inline-flex h-10 items-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-ink-inverse transition-colors hover:bg-[#3a3a36] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus focus-visible:ring-offset-2 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <span>Phân tích</span>
                    <ArrowRight className="size-4" aria-hidden="true" />
                  </button>
                </div>
              </div>

              {errorInfo && (
                <div
                  className="mt-4 rounded-xl border border-warning/40 bg-warning-soft px-4 py-3.5 text-sm text-text-warning"
                  role="alert"
                >
                  <div className="flex items-start gap-2 font-semibold">
                    <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                    <span>{errorInfo.message}</span>
                  </div>
                  {errorInfo.suggestions && errorInfo.suggestions.length > 0 && (
                    <div className="mt-2 pl-6">
                      <div className="text-xs font-medium text-text-secondary">Có thể hỏi:</div>
                      <div className="mt-1 flex flex-col items-start gap-1">
                        {errorInfo.suggestions.map((sug, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => {
                              setQuestion(sug);
                              setErrorInfo(null);
                              if (textareaRef.current) textareaRef.current.focus();
                            }}
                            className="text-left text-text-accent underline decoration-transparent underline-offset-2 hover:decoration-current"
                          >
                            {sug}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <p className="mt-3 mb-0 px-1 text-[13px] text-text-secondary">
                Dữ liệu hiện có: {entitiesStr} · {periodsStr} · {metricsStr} ·{' '}
                <Link
                  to="/data"
                  className="font-medium text-text-accent underline decoration-transparent underline-offset-2 hover:decoration-current"
                >
                  Chi tiết
                </Link>
              </p>

              {uploadId && uploadSuggestions.length > 0 ? (
                <section className="mt-12" aria-labelledby="suggest-upload-heading">
                  <h2 id="suggest-upload-heading" className="m-0 text-[15px] font-semibold text-text-primary">
                    {uploadEntity ? `Gợi ý cho ${uploadEntity}` : 'Gợi ý cho dữ liệu tải lên'}
                  </h2>
                  <ul className="mt-3 grid list-none grid-cols-1 gap-2 p-0 sm:grid-cols-2">
                    {uploadSuggestions.map((sug, idx) => (
                      <li key={idx}>
                        <button
                          type="button"
                          aria-label={sug}
                          onClick={() => {
                            setQuestion(sug);
                            setErrorInfo(null);
                            if (textareaRef.current) textareaRef.current.focus();
                          }}
                          className="group flex h-full w-full items-start gap-3 rounded-xl border border-border-subtle bg-surface-primary px-4 py-3 text-left transition-colors hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
                        >
                          <span className="min-w-0 flex-1">
                            <span className="block text-xs font-medium text-text-tertiary">Dữ liệu tải lên</span>
                            <span className="mt-0.5 block text-[14px] leading-snug text-text-primary">{sug}</span>
                          </span>
                          <ArrowUpRight
                            className="mt-0.5 size-4 shrink-0 text-text-tertiary transition-colors group-hover:text-text-primary"
                            aria-hidden="true"
                          />
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : (
                capabilities?.suggestedQuestions && capabilities.suggestedQuestions.length > 0 && (
                  <section className="mt-12" aria-labelledby="suggest-heading">
                    <h2 id="suggest-heading" className="m-0 text-[15px] font-semibold text-text-primary">
                      Thử hỏi
                    </h2>
                    <ul className="mt-3 grid list-none grid-cols-1 gap-2 p-0 sm:grid-cols-2">
                      {capabilities.suggestedQuestions.map((sug, idx) => (
                        <li key={idx}>
                          <button
                            type="button"
                            aria-label={sug}
                            onClick={() => {
                              setQuestion(sug);
                              setErrorInfo(null);
                              if (textareaRef.current) textareaRef.current.focus();
                            }}
                            className="group flex h-full w-full items-start gap-3 rounded-xl border border-border-subtle bg-surface-primary px-4 py-3 text-left transition-colors hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
                          >
                            <span className="min-w-0 flex-1">
                              <span className="block text-xs font-medium text-text-tertiary">{questionKind(sug)}</span>
                              <span className="mt-0.5 block text-[14px] leading-snug text-text-primary">{sug}</span>
                            </span>
                            <ArrowUpRight
                              className="mt-0.5 size-4 shrink-0 text-text-tertiary transition-colors group-hover:text-text-primary"
                              aria-hidden="true"
                            />
                          </button>
                        </li>
                      ))}
                    </ul>
                  </section>
                )
              )}

              <RecentReportsList />
            </div>
          ) : (
            <AnalysisSessionWorkspace
              streamRequest={{ query: question, upload_id: uploadId || undefined }}
              isLiveStream={isLiveStream}
              steps={fixtureSteps}
              capabilities={capabilities}
              onBackToComposer={() => {
                setMode('ASK');
                const resetParams: Record<string, string> = {};
                if (uploadId) resetParams.upload_id = uploadId;
                if (searchParams.get('entity')) resetParams.entity = searchParams.get('entity')!;
                if (searchParams.get('period')) resetParams.period = searchParams.get('period')!;
                setSearchParams(resetParams);
              }}
              onBlocked={(info) => {
                const message = info.code
                  ? mapErrorCodeToMessage(info.code, capabilities)
                  : info.message;
                setErrorInfo({ ...info, message: message || info.message });
                setMode('ASK');
                setSearchParams({});
              }}
            />
          )}
        </div>
      </div>
    </WorkspaceShell>
  );
}

function RecentReportsList() {
  const [runs, setRuns] = useState<
    Array<{ run_id: string; report_id?: string; query: string; created_at: string; status: string }>
  >([]);
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
        const base = baseUrl || origin;
        const res = await fetch(`${base}/api/runs?limit=5`, {
          headers: { Accept: 'application/json' }
        });
        if (res.ok) {
          const data = (await res.json()) as Array<{
            run_id: string;
            report_id?: string;
            query: string;
            created_at: string;
            status: string;
          }>;
          if (Array.isArray(data) && isMounted) {
            setRuns(data.slice(0, 5));
          }
        }
      } catch {
        // ignore
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    void fetchRuns();
    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading || runs.length === 0) return null;

  return (
    <section className="mt-12" aria-labelledby="recent-heading">
      <div className="flex items-baseline justify-between">
        <h2 id="recent-heading" className="m-0 text-[15px] font-semibold text-text-primary">
          Báo cáo gần đây
        </h2>
        <Link
          to="/reports"
          className="text-[13px] font-medium text-text-accent underline decoration-transparent underline-offset-2 hover:decoration-current"
        >
          Xem tất cả
        </Link>
      </div>
      <ul className="mt-3 list-none divide-y divide-border-subtle overflow-hidden rounded-xl border border-border-subtle bg-surface-primary p-0">
        {runs.map((r) => {
          const dateStr = formatDateDisplay(r.created_at);
          const statusText = mapRunStatusText(r.status);
          const targetId = r.report_id || r.run_id;
          return (
            <li key={r.run_id}>
              <Link
                to={`/reports/${targetId}`}
                className="flex items-center justify-between gap-4 px-4 py-3 no-underline transition-colors hover:bg-surface-secondary"
              >
                <span className="truncate text-[14px] text-text-primary">{r.query}</span>
                <span className="flex-none text-xs tabular-nums text-text-tertiary">
                  {dateStr} · {statusText}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function questionKind(question: string): string {
  const q = question.toLowerCase();
  if (q.includes('so sánh')) return 'So sánh hai ngân hàng';
  if (/nào có|cao nhất|thấp nhất|xếp hạng/.test(q)) return 'Xếp hạng nhóm';
  if (/thay đổi|xu hướng|diễn biến/.test(q)) return 'Xu hướng theo quý';
  if (/sức khỏe|so với các ngân hàng|hồ sơ/.test(q)) return 'Hồ sơ so với nhóm';
  return 'Tra cứu nhanh';
}

function mapRunStatusText(status?: string): string {
  switch (status?.toLowerCase()) {
    case 'completed':
    case 'success':
      return 'Hoàn tất';
    case 'accepted_with_limitations':
    case 'partial':
      return 'Có giới hạn';
    case 'error':
    case 'blocked':
      return 'Bị chặn';
    default:
      return 'Không rõ trạng thái';
  }
}

function formatDateDisplay(isoString?: string): string {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '—';
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    return `${day}/${month}`;
  } catch {
    return '—';
  }
}
