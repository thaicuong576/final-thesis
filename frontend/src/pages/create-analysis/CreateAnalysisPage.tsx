import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { WorkspaceShell } from '../../components/layout/WorkspaceShell';
import { useAnalysisCapabilities } from '../../features/create-analysis/hooks/useAnalysisCapabilities';
import { AnalysisSessionWorkspace } from '../../features/analysis-session/components/AnalysisSessionWorkspace';
import type { TraceStep } from '../../features/analysis-session/model/types';
import { mapErrorCodeToMessage } from '../../features/analysis-session/useTraceStream';
import { DEFAULT_METRICS } from '@/features/equity-report';
import { getApiBaseUrl } from '@/shared/lib/apiUrl';

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

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const placeholder =
    capabilities?.suggestedQuestions?.[0] ||
    'Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024';

  const entitiesStr =
    capabilities?.entities && capabilities.entities.length > 0
      ? capabilities.entities.map((e) => e.ticker || e.name || e.id).join(', ')
      : 'ACB, MBB, TCB, VCB, VPB';

  const periodsStr = (() => {
    if (!capabilities?.periods || capabilities.periods.length === 0) {
      return 'Q1–Q4/2024';
    }
    const years = Array.from(new Set(capabilities.periods.map((p) => p.year).filter(Boolean)));
    if (years.length === 1) {
      return `Q1–Q4/${years[0]}`;
    }
    return 'Q1–Q4/2024';
  })();

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
    setSearchParams({ q: trimmed });
    setIsLiveStream(true);
    setMode('SESSION');
  }, [question, setSearchParams]);

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
      <div className="min-h-[calc(100vh-80px)] bg-workspace py-8 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-[860px]">
          {mode === 'ASK' ? (
            <div className="bg-surface-secondary border border-line rounded-xl p-6 sm:p-8">
              {/* 1. Page Title */}
              <h1 className="text-2xl font-bold tracking-tight text-text-primary mb-3">
                Bạn muốn phân tích gì?
              </h1>

              {/* 2. Textarea and Primary Analyze Button */}
              <div className="border border-border-strong rounded-lg p-3 sm:p-3.5 bg-surface-primary shadow-sm focus-within:ring-1 focus-within:ring-border-accent focus-within:border-border-accent transition-all">
                <textarea
                  ref={textareaRef}
                  value={question}
                  onChange={handleInput}
                  onKeyDown={handleKeyDown}
                  rows={3}
                  placeholder={placeholder}
                  className="w-full resize-none border-none bg-transparent p-0 text-[15px] leading-relaxed text-text-primary placeholder:text-text-muted focus:outline-none min-h-[56px]"
                  aria-label="Câu hỏi phân tích"
                />
                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={handleAnalyze}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-ink text-ink-inverse font-semibold text-sm rounded shadow-sm hover:bg-[#343430] active:translate-y-[1px] transition-all cursor-pointer"
                  >
                    <span>Phân tích</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Error Block for RUN_BLOCKED or error status */}
              {errorInfo && (
                <div
                  className="mt-3 p-3.5 bg-warning-soft/60 border border-warning rounded-lg text-xs space-y-2 text-text-warning"
                  role="alert"
                >
                  <div className="font-semibold text-text-warning">{errorInfo.message}</div>
                  {errorInfo.suggestions && errorInfo.suggestions.length > 0 && (
                    <div className="space-y-1">
                      <div className="text-text-muted text-[11px] font-medium">Gợi ý câu hỏi hợp lệ:</div>
                      <div className="flex flex-col gap-1">
                        {errorInfo.suggestions.map((sug, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => {
                              setQuestion(sug);
                              setErrorInfo(null);
                              if (textareaRef.current) textareaRef.current.focus();
                            }}
                            className="text-left text-text-accent hover:underline cursor-pointer"
                          >
                            • {sug}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 3. Availability Information */}
              <p className="text-[13px] text-text-secondary mt-2 mb-6">
                Dữ liệu hiện có: {entitiesStr} · {periodsStr} · {metricsStr} ·{' '}
                <Link to="/data" className="text-text-accent hover:underline font-medium">
                  Chi tiết
                </Link>
              </p>

              {/* 4. Suggested Questions (Rendered only if backend provides them) */}
              {capabilities?.suggestedQuestions && capabilities.suggestedQuestions.length > 0 && (
                <div className="space-y-2 mb-6">
                  <div className="text-[13px] text-text-secondary font-medium">Thử hỏi</div>
                  <div className="flex flex-col gap-1 text-[13px]">
                    {capabilities.suggestedQuestions.map((sug, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => {
                          setQuestion(sug);
                          setErrorInfo(null);
                          if (textareaRef.current) textareaRef.current.focus();
                        }}
                        className="text-left text-text-primary hover:text-text-accent py-0.5 transition-colors"
                      >
                        {sug}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* 5. Recent Reports */}
              <RecentReportsList />
            </div>
          ) : (
            <AnalysisSessionWorkspace
              streamRequest={{ query: question }}
              isLiveStream={isLiveStream}
              steps={fixtureSteps}
              capabilities={capabilities}
              onBackToComposer={() => {
                setMode('ASK');
                setSearchParams({});
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
    <div className="space-y-2 mt-6">
      <div className="text-[13px] text-text-secondary font-medium">Báo cáo gần đây</div>
      <div className="divide-y divide-border border-t border-line text-[13px]">
        {runs.map((r) => {
          const dateStr = formatDateDisplay(r.created_at);
          const statusText = mapRunStatusText(r.status);
          const targetId = r.report_id || r.run_id;

          return (
            <Link
              key={r.run_id}
              to={`/reports/${targetId}`}
              className="flex justify-between items-center py-2.5 hover:bg-surface-tertiary transition-colors no-underline block"
            >
              <span className="text-text-primary font-normal truncate pr-4">{r.query}</span>
              <span className="text-text-muted flex-none text-xs">
                {dateStr} · {statusText}
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
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
