import { Fragment, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowRight, Database, Loader2 } from 'lucide-react';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import { PageCrumbs } from '@/components/layout/PageCrumbs';
import { Button } from '@/components/ui/button';
import { useAnalysisCapabilities } from '@/features/create-analysis/hooks/useAnalysisCapabilities';
import { BankUploadSection } from '@/features/onboarding/BankUploadSection';
import { FilingWizard } from '@/features/ingest';
import type { CoverageItem, Entity, Metric } from '@/entities/capability/model/types';
import { analyticalPeriodIds, formatQuarter } from '@/entities/capability/model/coverage';

const CORE_METRICS = 4;

/** Plain-language definitions shown to readers; formulas match the versioned code formulas. */
const METRIC_DEFINITIONS: Record<string, { name: string; formula: string }> = {
  'bank.npl_g35': {
    name: 'Tỷ lệ nợ xấu',
    formula: 'Dư nợ nhóm 3–5 / tổng dư nợ cho vay khách hàng',
  },
  'bank.llr_coverage': {
    name: 'Tỷ lệ bao phủ nợ xấu',
    formula: 'Dự phòng rủi ro cho vay khách hàng / dư nợ nhóm 3–5',
  },
  'bank.roa': {
    name: 'Tỷ suất sinh lời trên tổng tài sản (ROA)',
    formula: 'Lợi nhuận sau thuế 4 quý gần nhất / tổng tài sản bình quân',
  },
  'bank.roe': {
    name: 'Tỷ suất sinh lời trên vốn chủ sở hữu (ROE)',
    formula: 'Lợi nhuận của cổ đông ngân hàng mẹ 4 quý gần nhất / vốn chủ sở hữu bình quân',
  },
};

function metricSymbol(metric: Metric): string {
  if (metric.id === 'bank.npl_g35') return 'NPL';
  if (metric.id === 'bank.llr_coverage') return 'LLR';
  return (metric.acronym || metric.shortLabel || metric.id).replace(/_.*$/, '');
}

function directionLabel(direction?: string): string {
  if (direction === 'higher_is_better') return 'Càng cao càng tốt';
  if (direction === 'lower_is_better') return 'Càng thấp càng tốt';
  return 'Theo dõi';
}

interface MatrixProps {
  coverage: CoverageItem[];
  entities: Entity[];
  periodIds: string[];
}

function CoverageMatrix({ coverage, entities, periodIds }: MatrixProps) {
  const byCell = useMemo(() => {
    const map = new Map<string, number>();
    for (const c of coverage) map.set(`${c.entity_id.toUpperCase()}:${c.period_id}`, c.metrics?.length ?? 0);
    return map;
  }, [coverage]);
  const banks = useMemo(
    () => [...entities].sort((a, b) => (a.ticker || a.id).localeCompare(b.ticker || b.id)),
    [entities]
  );
  const years = useMemo(() => {
    const out: { year: string; count: number }[] = [];
    for (const p of periodIds) {
      const y = p.slice(0, 4);
      const last = out[out.length - 1];
      if (last && last.year === y) last.count += 1;
      else out.push({ year: y, count: 1 });
    }
    return out;
  }, [periodIds]);
  const latest = periodIds[periodIds.length - 1];

  return (
    <div className="w-full min-w-0 overflow-x-auto" data-testid="coverage-matrix-scroll">
      <table className="w-full min-w-[620px] border-separate border-spacing-0 text-xs" data-testid="coverage-matrix-table">
        <caption className="sr-only">Độ phủ số liệu theo ngân hàng và quý</caption>
        <thead>
          <tr>
            <th scope="col" rowSpan={2} className="sticky left-0 z-20 w-20 whitespace-nowrap bg-card pb-2 pr-3 text-left align-bottom font-semibold text-ink-secondary">
              Ngân hàng
            </th>
            {years.map((y) => (
              <th
                key={y.year}
                scope="colgroup"
                colSpan={y.count}
                className="border-b border-line pb-1 text-center font-mono text-[11px] font-semibold tracking-wide text-ink-secondary"
              >
                {y.year}
              </th>
            ))}
            <th scope="col" rowSpan={2} className="w-16 whitespace-nowrap pb-2 pl-3 text-right align-bottom font-semibold text-ink-secondary">
              Đủ số liệu
            </th>
          </tr>
          <tr>
            {periodIds.map((p) => (
              <th
                key={p}
                scope="col"
                className={`pt-1.5 pb-2 text-center font-mono text-[11px] font-semibold ${p === latest ? 'text-text-accent' : 'text-ink-tertiary'}`}
              >
                Q{p.slice(-1)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {banks.map((bank) => {
            const key = (bank.ticker || bank.id).toUpperCase();
            const full = periodIds.filter((p) => (byCell.get(`${key}:${p}`) ?? 0) >= CORE_METRICS).length;
            return (
              <tr key={bank.id}>
                <th scope="row" className="sticky left-0 z-10 bg-card py-[3px] pr-3 text-left font-mono text-[12px] font-semibold text-ink" title={bank.name}>
                  {bank.ticker || bank.id}
                </th>
                {periodIds.map((p) => {
                  const n = byCell.get(`${key}:${p}`) ?? 0;
                  const quarter = formatQuarter(p);
                  const state = n >= CORE_METRICS ? 'full' : n > 0 ? 'partial' : 'missing';
                  const label =
                    state === 'full'
                      ? `${key} ${quarter}: đủ ${CORE_METRICS} chỉ tiêu`
                      : state === 'partial'
                        ? `${key} ${quarter}: có ${n}/${CORE_METRICS} chỉ tiêu`
                        : `${key} ${quarter}: chưa có báo cáo`;
                  return (
                    <td key={p} className="px-[3px] py-[3px]">
                      <div
                        role="img"
                        aria-label={label}
                        title={label}
                        data-state={state}
                        className={
                          state === 'full'
                            ? 'flex h-7 items-center justify-center rounded-sm bg-ready-soft'
                            : state === 'partial'
                              ? 'flex h-7 items-center justify-center rounded-sm bg-warning-soft font-mono text-[10px] font-semibold text-text-warning'
                              : 'flex h-7 items-center justify-center rounded-sm border border-dashed border-border-strong bg-surface-secondary font-mono text-[11px] text-ink-tertiary'
                        }
                      >
                        {state === 'full' ? (
                          <span className="size-1.5 rounded-full bg-ready" aria-hidden="true" />
                        ) : state === 'partial' ? (
                          `${n}/${CORE_METRICS}`
                        ) : (
                          '–'
                        )}
                      </div>
                    </td>
                  );
                })}
                <td className="py-[3px] pl-3 text-right font-mono text-[12px] tabular-nums text-ink-secondary">
                  {full}/{periodIds.length}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function DataPage() {
  const capabilitiesQuery = useAnalysisCapabilities();
  const [uploadMethod, setUploadMethod] = useState<'pdf' | 'csv'>('pdf');

  useEffect(() => {
    const previousTitle = document.title;
    document.title = 'Dữ liệu · Phân tích tài chính';
    return () => {
      document.title = previousTitle;
    };
  }, []);

  const capabilities = capabilitiesQuery.data;
  const periodIds = useMemo(() => (capabilities ? analyticalPeriodIds(capabilities) : []), [capabilities]);
  const coverage = capabilities?.coverage ?? [];
  const bankCount = capabilities?.entities.length ?? 0;
  const cells = bankCount * periodIds.length;
  const fullCells = coverage.filter(
    (c) => periodIds.includes(c.period_id) && (c.metrics?.length ?? 0) >= CORE_METRICS
  ).length;
  const missingCells = cells - fullCells;
  const range = periodIds.length ? `${formatQuarter(periodIds[0])} – ${formatQuarter(periodIds[periodIds.length - 1])}` : '';

  const isEmpty =
    Boolean(capabilities) &&
    !capabilitiesQuery.isPending &&
    !capabilitiesQuery.isError &&
    capabilities!.entities.length === 0 &&
    capabilities!.metrics.length === 0;

  return (
    <WorkspaceShell activeSection="data" context={<PageCrumbs items={[{ label: 'Dữ liệu' }]} />}>
      <div className="min-h-[calc(100vh-80px)] w-full max-w-full min-w-0 overflow-x-hidden px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-[1080px] min-w-0 space-y-6">
          <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div className="min-w-0">
              <p className="m-0 font-mono text-[11px] font-semibold uppercase tracking-[0.08em] text-text-accent">Phạm vi dữ liệu</p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-ink">Dữ liệu đang dùng để phân tích</h1>
              <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-ink-secondary">
                Số liệu lấy từ báo cáo tài chính hợp nhất của từng ngân hàng, đối chiếu tới số trang. Mọi con số trong báo cáo
                phân tích đều nằm trong bảng dưới đây; quý nào chưa có báo cáo thì để trống, không ước tính.
              </p>
            </div>
            {capabilities?.analysis_available === true && (
              <Button asChild className="h-9 w-fit shrink-0 border border-amber-border bg-amber px-3 text-xs font-semibold text-ink hover:bg-amber-hover">
                <Link to="/analysis">
                  Đặt câu hỏi <ArrowRight className="ml-1 size-3.5" aria-hidden="true" />
                </Link>
              </Button>
            )}
          </header>

          {capabilitiesQuery.isPending && (
            <div className="flex items-center gap-3 rounded-md border border-line bg-card p-5 text-sm text-ink-secondary" role="status">
              <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden="true" />
              <span>Đang tải phạm vi dữ liệu…</span>
            </div>
          )}

          {capabilitiesQuery.isError && (
            <div className="rounded-md border border-warning/40 bg-card p-5" role="alert">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden="true" />
                <div className="min-w-0 flex-1 space-y-3">
                  <h2 className="text-sm font-bold text-ink">Không tải được phạm vi dữ liệu</h2>
                  <p className="text-sm text-ink-secondary break-words">
                    {capabilitiesQuery.error instanceof Error
                      ? capabilitiesQuery.error.message
                      : 'Máy chủ chưa phản hồi. Hãy thử tải lại.'}
                  </p>
                  <Button type="button" variant="outline" onClick={() => void capabilitiesQuery.refetch()} className="border-line text-xs font-medium">
                    Thử tải lại
                  </Button>
                </div>
              </div>
            </div>
          )}

          {isEmpty && (
            <div className="rounded-md border border-line bg-card p-8 text-center" role="region" aria-label="Dữ liệu rỗng">
              <Database className="mx-auto size-8 text-ink-tertiary" aria-hidden="true" />
              <h2 className="mt-3 text-base font-bold text-ink">Chưa có dữ liệu phân tích</h2>
              <p className="mx-auto mt-1 max-w-md text-sm text-ink-secondary">Máy chủ chưa nạp bộ dữ liệu đã kiểm định.</p>
            </div>
          )}

          {capabilities && !capabilitiesQuery.isError && !isEmpty && (
            <>
              {capabilities.analysis_available !== true && (
                <div className="rounded-md border border-warning/40 bg-warning-soft/50 p-4" role="alert">
                  <h2 className="text-sm font-bold text-ink">Chưa thể chạy phân tích</h2>
                  <p className="mt-1 text-sm text-ink-secondary">Bộ dữ liệu vẫn hiển thị để tham khảo, nhưng máy chủ chưa sẵn sàng phân tích.</p>
                </div>
              )}

              <dl className="grid grid-cols-2 overflow-hidden rounded-md border border-line bg-card sm:grid-cols-4" data-testid="dataset-stats">
                {[
                  ['Ngân hàng', String(bankCount), 'niêm yết, cùng một nhóm so sánh'],
                  ['Kỳ', String(periodIds.length || '—'), range || 'chưa công bố'],
                  ['Chỉ tiêu', String(capabilities.metrics.length), 'chất lượng tài sản và sinh lời'],
                  ['Độ phủ', cells ? `${fullCells}/${cells}` : '—', missingCells > 0 ? `${missingCells} ô ngân hàng–quý chưa có báo cáo` : 'đủ mọi ngân hàng – quý'],
                ].map(([label, value, note], i) => (
                  <div key={label} className={`p-4 ${i % 2 ? 'border-l' : ''} ${i > 1 ? 'border-t sm:border-t-0' : ''} ${i === 2 ? 'sm:border-l' : ''} border-line`}>
                    <dt className="text-xs text-ink-secondary">{label}</dt>
                    <dd className="m-0 mt-1 font-mono text-2xl font-semibold tabular-nums text-ink">{value}</dd>
                    <dd className="m-0 mt-0.5 text-[11px] leading-snug text-ink-tertiary">{note}</dd>
                  </div>
                ))}
              </dl>

              {coverage.length > 0 && periodIds.length > 0 && (
                <section className="rounded-md border border-line bg-card p-4 sm:p-6" aria-labelledby="coverage-heading">
                  <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <h2 id="coverage-heading" className="m-0 text-base font-bold text-ink">Độ phủ theo quý</h2>
                      <p className="mt-1 text-xs text-ink-secondary">
                        Mỗi ô là một ngân hàng trong một quý. Ô đầy đủ có cả {CORE_METRICS} chỉ tiêu, mỗi chỉ tiêu được tính lại từ số liệu gốc.
                      </p>
                    </div>
                    <ul className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0 text-[11px] text-ink-secondary" aria-label="Chú thích">
                      <li className="flex items-center gap-1.5"><span className="inline-flex h-3 w-4 items-center justify-center rounded-sm bg-ready-soft" aria-hidden="true"><span className="size-1 rounded-full bg-ready" /></span>Đủ {CORE_METRICS} chỉ tiêu</li>
                      <li className="flex items-center gap-1.5"><span className="inline-block h-3 w-4 rounded-sm bg-warning-soft" aria-hidden="true" />Thiếu một phần</li>
                      <li className="flex items-center gap-1.5"><span className="inline-block h-3 w-4 rounded-sm border border-dashed border-border-strong bg-surface-secondary" aria-hidden="true" />Chưa có báo cáo</li>
                    </ul>
                  </div>
                  <CoverageMatrix coverage={coverage} entities={capabilities.entities} periodIds={periodIds} />
                </section>
              )}

              <section className="rounded-md border border-line bg-card p-4 sm:p-6" aria-labelledby="metrics-heading">
                <h2 id="metrics-heading" className="m-0 text-base font-bold text-ink">Chỉ tiêu và cách tính</h2>
                <dl className="mt-4 grid gap-px overflow-hidden rounded border border-line bg-line sm:grid-cols-2">
                  {capabilities.metrics.map((metric) => {
                    const def = METRIC_DEFINITIONS[metric.id];
                    return (
                      <div key={metric.id} className="bg-card p-4">
                        <dt className="flex items-baseline gap-2">
                          <span className="font-mono text-xs font-semibold text-text-accent">{metricSymbol(metric)}</span>
                          <span className="text-sm font-semibold text-ink">{def?.name || metric.label}</span>
                        </dt>
                        {def && <dd className="m-0 mt-1.5 text-xs leading-relaxed text-ink-secondary">{def.formula}</dd>}
                        <dd className="m-0 mt-1 text-[11px] text-ink-tertiary">
                          {metric.groupLabel || metric.group || 'Chung'} · {directionLabel(metric.direction)}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
              </section>

              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2 border-b border-line pb-2" role="tablist" aria-label="Phương thức nạp số liệu ngân hàng mới">
                  <button
                    type="button"
                    role="tab"
                    id="tab-ingest-pdf"
                    aria-selected={uploadMethod === 'pdf'}
                    aria-controls="panel-ingest-pdf"
                    onClick={() => setUploadMethod('pdf')}
                    className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors cursor-pointer ${
                      uploadMethod === 'pdf'
                        ? 'bg-amber text-ink border border-amber-border shadow-tactile'
                        : 'bg-surface-secondary text-ink-secondary hover:bg-surface-hover border border-line'
                    }`}
                  >
                    Báo cáo tài chính PDF (Đường ống OCR)
                  </button>
                  <button
                    type="button"
                    role="tab"
                    id="tab-ingest-csv"
                    aria-selected={uploadMethod === 'csv'}
                    aria-controls="panel-ingest-csv"
                    onClick={() => setUploadMethod('csv')}
                    className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors cursor-pointer ${
                      uploadMethod === 'csv'
                        ? 'bg-amber text-ink border border-amber-border shadow-tactile'
                        : 'bg-surface-secondary text-ink-secondary hover:bg-surface-hover border border-line'
                    }`}
                  >
                    Tệp bảng tính CSV (Đã đối chiếu sẵn)
                  </button>
                </div>

                <div
                  id={uploadMethod === 'pdf' ? 'panel-ingest-pdf' : 'panel-ingest-csv'}
                  role="tabpanel"
                  aria-labelledby={uploadMethod === 'pdf' ? 'tab-ingest-pdf' : 'tab-ingest-csv'}
                >
                  {uploadMethod === 'pdf' ? (
                    <FilingWizard />
                  ) : (
                    <BankUploadSection capabilities={capabilities} />
                  )}
                </div>
              </div>

              <details className="group rounded-md border border-line bg-surface-secondary px-4 py-3 text-xs text-ink-secondary sm:px-5">
                <summary className="cursor-pointer select-none font-semibold text-ink">Chi tiết kỹ thuật</summary>
                <dl className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-[max-content_1fr]">
                  {[
                    ['Mã bộ dữ liệu', capabilities.datasetId || '—'],
                    ['Mã bản chụp', capabilities.dataset_snapshot_id || capabilities.datasetSnapshotId || '—'],
                    ['Nguồn', capabilities.source || '—'],
                    ['Kho dữ liệu', capabilities.database_status || '—'],
                  ].map(([k, v]) => (
                    <Fragment key={k}>
                      <dt className="text-ink-tertiary">{k}</dt>
                      <dd className="m-0 break-all font-mono text-[11px] text-ink-secondary">{v}</dd>
                    </Fragment>
                  ))}
                </dl>
              </details>
            </>
          )}
        </div>
      </div>
    </WorkspaceShell>
  );
}
