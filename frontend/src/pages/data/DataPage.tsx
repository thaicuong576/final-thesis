import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowRight, Check, Database, FileText, Loader2 } from 'lucide-react';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import { Button } from '@/components/ui/button';
import { useAnalysisCapabilities } from '@/features/create-analysis/hooks/useAnalysisCapabilities';
import { formatPeriodsSignature } from '@/features/analysis-composer/model/intentParser';
import type { AnalysisCapabilities, Entity, Period } from '@/entities/capability/model/types';

function getCellCoverageStatus(
  capabilities: AnalysisCapabilities,
  entity: Entity,
  period: Period
): { isCovered: boolean; label: string } {
  if (
    capabilities.analysis_available === false &&
    !entity.periods &&
    !entity.coverage &&
    !capabilities.coverageMatrix &&
    !capabilities.coverage
  ) {
    return {
      isCovered: false,
      label: 'chưa có số liệu đã kiểm định'
    };
  }

  const matrix = capabilities.coverageMatrix ?? capabilities.coverage;
  if (matrix) {
    const entityCoverage = matrix[entity.ticker] ?? matrix[entity.id];
    if (Array.isArray(entityCoverage)) {
      const isCovered = entityCoverage.includes(period.id);
      return {
        isCovered,
        label: isCovered ? 'Đã kiểm định' : 'chưa có số liệu đã kiểm định'
      };
    }
    if (entityCoverage && typeof entityCoverage === 'object') {
      const val = entityCoverage[period.id];
      const isCovered = val === true || val === 'valid';
      return {
        isCovered,
        label: isCovered ? 'Đã kiểm định' : 'chưa có số liệu đã kiểm định'
      };
    }
  }

  const entityPeriods = entity.periods ?? entity.coveredPeriods;
  if (Array.isArray(entityPeriods)) {
    const periodIds = entityPeriods.map((p) => (typeof p === 'string' ? p : (p as Period).id));
    const isCovered = periodIds.includes(period.id);
    return {
      isCovered,
      label: isCovered ? 'Đã kiểm định' : 'chưa có số liệu đã kiểm định'
    };
  }

  if (Array.isArray(entity.missingPeriods)) {
    if (entity.missingPeriods.includes(period.id)) {
      return {
        isCovered: false,
        label: 'chưa có số liệu đã kiểm định'
      };
    }
  }

  if (entity.coverage && typeof entity.coverage === 'object') {
    const val = entity.coverage[period.id];
    const isCovered = val === true || val === 'valid';
    return {
      isCovered,
      label: isCovered ? 'Đã kiểm định' : 'chưa có số liệu đã kiểm định'
    };
  }

  if (capabilities.analysis_available === true) {
    return {
      isCovered: true,
      label: 'Đã kiểm định'
    };
  }

  return {
    isCovered: false,
    label: 'chưa có số liệu đã kiểm định'
  };
}

function getDirectionLabel(direction?: string): string {
  if (direction === 'higher_is_better') return 'Càng cao càng tốt';
  if (direction === 'lower_is_better') return 'Càng thấp càng tốt';
  if (direction === 'neutral') return 'Trung tính';
  return 'Theo dõi';
}

export function DataPage() {
  const capabilitiesQuery = useAnalysisCapabilities();

  useEffect(() => {
    const previousTitle = document.title;
    document.title = 'Dữ liệu phân tích · Phân tích tài chính';
    return () => {
      document.title = previousTitle;
    };
  }, []);

  const capabilities = capabilitiesQuery.data;
  const runnableCapabilities = new Set(
    capabilities?.analysis_available === true ? capabilities.implemented_capabilities ?? [] : []
  );
  const canRunPeerAnalysis = runnableCapabilities.has('sector');
  const canRunMacroAnalysis = runnableCapabilities.has('macro');

  const isEmpty =
    Boolean(capabilities) &&
    !capabilitiesQuery.isPending &&
    !capabilitiesQuery.isError &&
    capabilities!.entities.length === 0 &&
    capabilities!.metrics.length === 0 &&
    capabilities!.periods.length === 0;

  const hasCoverageInfo = Boolean(capabilities && capabilities.entities.length > 0 && capabilities.periods.length > 0);

  return (
    <WorkspaceShell activeSection="data" context={<span className="text-xs font-bold text-ink">DỮ LIỆU PHÂN TÍCH</span>}>
      <div className="min-h-[calc(100vh-80px)] bg-workspace px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-[1120px] space-y-6">
          <header className="border-b border-line pb-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">Dữ liệu phân tích</h1>
                <p className="mt-1 max-w-2xl text-sm text-ink-secondary">
                  Catalog dưới đây do API công bố. Chỉ có thể chạy phân tích khi API xác nhận snapshot dữ liệu đã kiểm định và năng lực tương ứng.
                </p>
              </div>
              {capabilities?.analysis_available === true && (
                <Button asChild className="h-9 w-fit border border-amber-border bg-amber px-3 text-xs font-semibold text-ink hover:bg-amber-hover shrink-0">
                  <Link to="/analysis">
                    Tạo phân tích <ArrowRight className="ml-1 size-3.5" aria-hidden="true" />
                  </Link>
                </Button>
              )}
            </div>
          </header>

          {capabilitiesQuery.isPending && (
            <div className="flex items-center gap-3 rounded-md border border-line bg-card p-5 text-sm text-ink-secondary" role="status">
              <Loader2 className="size-4 animate-spin text-ink-secondary" aria-hidden="true" />
              <span>Đang tải phạm vi dữ liệu từ hệ thống…</span>
            </div>
          )}

          {capabilitiesQuery.isError && (
            <div className="rounded-md border border-warning/40 bg-card p-5" role="alert">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden="true" />
                <div className="space-y-3">
                  <h2 className="text-sm font-bold text-ink">Không thể xác định dữ liệu đang hỗ trợ</h2>
                  <p className="text-sm text-ink-secondary">
                    {capabilitiesQuery.error instanceof Error
                      ? capabilitiesQuery.error.message
                      : 'Không thể xác nhận phạm vi từ API. Hãy thử tải lại trước khi tạo phân tích.'}
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void capabilitiesQuery.refetch()}
                    className="border-line text-xs font-medium"
                  >
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
              <p className="mx-auto mt-1 max-w-md text-sm text-ink-secondary">
                API hiện chưa công bố dữ liệu hoặc snapshot đã kiểm định nào. Hãy kiểm tra kết nối với kho dữ liệu.
              </p>
            </div>
          )}

          {capabilities && !capabilitiesQuery.isError && !isEmpty && (
            <>
              {capabilities.analysis_available !== true && (
                <div className="rounded-md border border-warning/40 bg-warning-soft/50 p-4" role="alert">
                  <h2 className="text-sm font-bold text-ink">Chưa thể chạy phân tích trên dữ liệu hiện tại</h2>
                  <p className="mt-1 text-sm text-ink-secondary">
                    API chưa xác nhận snapshot đã kiểm định có thể chạy. Catalog vẫn hiển thị để tham khảo; trạng thái kho dữ liệu: {capabilities.database_status || 'chưa được API công bố'}.
                  </p>
                </div>
              )}

              {/* Section 1: Catalog & Snapshot Overview */}
              <section className="rounded-md border border-line bg-card p-5 sm:p-6" aria-labelledby="dataset-heading">
                <div className="flex flex-col gap-4 border-b border-line pb-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <Database className="size-4 text-ink-secondary" aria-hidden="true" />
                      <h2 id="dataset-heading" className="text-base font-bold text-ink">Catalog năng lực API</h2>
                    </div>
                    <p className="mt-2 break-all font-mono text-xs text-ink-secondary">
                      {capabilities.dataset_snapshot_id
                        ? `Snapshot đã kiểm định: ${capabilities.dataset_snapshot_id}`
                        : `Mã catalog: ${capabilities.snapshotId || 'chưa công bố'} · Snapshot đã kiểm định: chưa công bố`}
                    </p>
                  </div>
                  <Button asChild className="h-9 w-fit border border-amber-border bg-amber px-3 text-xs font-semibold text-ink hover:bg-amber-hover shrink-0">
                    <Link to="/analysis">
                      Tạo phân tích <ArrowRight className="ml-1 size-3.5" aria-hidden="true" />
                    </Link>
                  </Button>
                </div>

                <dl className="grid grid-cols-2 gap-4 py-5 text-sm sm:grid-cols-4">
                  <div>
                    <dt className="text-xs text-ink-secondary">Ngân hàng</dt>
                    <dd className="mt-1 font-semibold text-ink">{capabilities.entities.length}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-ink-secondary">Kỳ dữ liệu</dt>
                    <dd className="mt-1 font-semibold text-ink">{formatPeriodsSignature(capabilities.periods) || 'Chưa công bố'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-ink-secondary">Chỉ tiêu</dt>
                    <dd className="mt-1 font-semibold text-ink">{capabilities.metrics.length}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-ink-secondary">Phân tích khả dụng</dt>
                    <dd className="mt-1 font-semibold text-ink">{capabilities.analysis_available === true ? 'Có' : 'Chưa xác nhận'}</dd>
                  </div>
                </dl>

                <div className="grid gap-5 border-t border-line pt-5 text-sm sm:grid-cols-2">
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Ngân hàng trong catalog</h3>
                    <p className="mt-2 leading-relaxed text-ink">{capabilities.entities.map((entity) => entity.ticker).join(' · ') || 'Chưa công bố'}</p>
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Chỉ tiêu trong catalog</h3>
                    <p className="mt-2 leading-relaxed text-ink">{capabilities.metrics.map((metric) => metric.acronym).join(' · ') || 'Chưa công bố'}</p>
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Nhóm tham chiếu</h3>
                    <p className="mt-2 text-ink">
                      {canRunPeerAnalysis
                        ? capabilities.peerUniverse?.label || 'API chưa công bố nhóm tham chiếu'
                        : 'API chưa xác nhận phân tích nhóm tham chiếu có thể chạy.'}
                    </p>
                    {canRunPeerAnalysis && capabilities.peerUniverse?.description && (
                      <p className="mt-1 text-xs text-ink-secondary">{capabilities.peerUniverse.description}</p>
                    )}
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Bối cảnh vĩ mô</h3>
                    <p className="mt-2 text-ink">
                      {canRunMacroAnalysis
                        ? capabilities.macro.summary
                        : 'API chưa xác nhận năng lực phân tích vĩ mô có thể chạy.'}
                    </p>
                    {canRunMacroAnalysis && <p className="mt-1 text-xs text-ink-secondary">{capabilities.macro.details}</p>}
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Năng lực API xác nhận</h3>
                    <p className="mt-2 text-ink">
                      {capabilities.implemented_capabilities?.length
                        ? capabilities.implemented_capabilities.join(' · ')
                        : 'Chưa công bố'}
                    </p>
                    <p className="mt-1 text-xs text-ink-secondary">Trạng thái kho dữ liệu: {capabilities.database_status || 'chưa được API công bố'}</p>
                  </div>
                </div>
              </section>

              {/* Section 2: Ma trận độ phủ doanh nghiệp × kỳ */}
              <section className="rounded-md border border-line bg-card p-5 sm:p-6" aria-labelledby="coverage-heading">
                <div className="border-b border-line pb-3">
                  <h2 id="coverage-heading" className="text-base font-bold text-ink">Ma trận độ phủ doanh nghiệp × kỳ</h2>
                  <p className="mt-1 text-xs text-ink-secondary">
                    Độ phủ dữ liệu thực tế theo từng doanh nghiệp và kỳ báo cáo. Các ô thiếu được ghi nhận tường minh, không suy diễn hoặc nội suy.
                  </p>
                </div>

                {hasCoverageInfo ? (
                  <div className="mt-4 overflow-x-auto -mx-5 px-5 sm:mx-0 sm:px-0">
                    <table className="w-full min-w-[500px] border-collapse text-left text-xs sm:text-sm">
                      <thead>
                        <tr className="border-b border-line bg-surface-secondary text-ink-secondary">
                          <th scope="col" className="py-2.5 px-3 font-semibold">Doanh nghiệp</th>
                          {capabilities.periods.map((period) => (
                            <th key={period.id} scope="col" className="py-2.5 px-3 text-center font-semibold">
                              {period.label || period.id}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line">
                        {capabilities.entities.map((entity) => (
                          <tr key={entity.id || entity.ticker} className="hover:bg-surface-hover/50">
                            <td className="py-2.5 px-3">
                              <span className="font-semibold text-ink">{entity.ticker}</span>
                              {entity.name && <span className="block text-xs text-ink-secondary">{entity.name}</span>}
                            </td>
                            {capabilities.periods.map((period) => {
                              const status = getCellCoverageStatus(capabilities, entity, period);
                              return (
                                <td key={period.id} className="py-2.5 px-3 text-center">
                                  {status.isCovered ? (
                                    <span className="inline-flex items-center gap-1 rounded bg-ready-soft px-2 py-0.5 text-xs font-medium text-text-success border border-ready/20">
                                      <Check className="size-3" aria-hidden="true" />
                                      <span>{status.label}</span>
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center rounded border border-line bg-surface-secondary px-2 py-0.5 text-xs text-ink-secondary">
                                      {status.label}
                                    </span>
                                  )}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="mt-4 text-xs text-ink-secondary">API chưa cung cấp đủ thông tin doanh nghiệp và kỳ để lập ma trận độ phủ.</p>
                )}
              </section>

              {/* Section 3: Danh sách doanh nghiệp */}
              <section className="rounded-md border border-line bg-card p-5 sm:p-6" aria-labelledby="entities-heading">
                <div className="border-b border-line pb-3">
                  <h2 id="entities-heading" className="text-base font-bold text-ink">Danh sách doanh nghiệp ({capabilities.entities.length})</h2>
                  <p className="mt-1 text-xs text-ink-secondary">Các thực thể tài chính niêm yết trong phạm vi phân tích của snapshot.</p>
                </div>
                <div className="mt-4 overflow-x-auto -mx-5 px-5 sm:mx-0 sm:px-0">
                  <table className="w-full min-w-[420px] border-collapse text-left text-xs sm:text-sm">
                    <thead>
                      <tr className="border-b border-line bg-surface-secondary text-ink-secondary">
                        <th scope="col" className="py-2.5 px-3 font-semibold">Mã (Ticker)</th>
                        <th scope="col" className="py-2.5 px-3 font-semibold">Tên doanh nghiệp</th>
                        <th scope="col" className="py-2.5 px-3 font-semibold">Loại thực thể</th>
                        <th scope="col" className="py-2.5 px-3 font-semibold">Mã định danh</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {capabilities.entities.map((entity) => (
                        <tr key={entity.id || entity.ticker} className="hover:bg-surface-hover/50">
                          <td className="py-2.5 px-3 font-bold text-ink">{entity.ticker}</td>
                          <td className="py-2.5 px-3 text-ink">{entity.name || '—'}</td>
                          <td className="py-2.5 px-3 text-ink-secondary">{entity.type === 'company' ? 'Ngân hàng niêm yết' : (entity.type || 'Doanh nghiệp')}</td>
                          <td className="py-2.5 px-3 font-mono text-xs text-ink-secondary">{entity.id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* Section 4: Danh mục chỉ tiêu tài chính */}
              <section className="rounded-md border border-line bg-card p-5 sm:p-6" aria-labelledby="metrics-heading">
                <div className="border-b border-line pb-3">
                  <h2 id="metrics-heading" className="text-base font-bold text-ink">Chỉ tiêu tài chính ({capabilities.metrics.length})</h2>
                  <p className="mt-1 text-xs text-ink-secondary">Các chỉ số được định nghĩa theo chuẩn tài chính, có nhãn tiếng Việt và đơn vị đo rõ ràng.</p>
                </div>
                <div className="mt-4 overflow-x-auto -mx-5 px-5 sm:mx-0 sm:px-0">
                  <table className="w-full min-w-[500px] border-collapse text-left text-xs sm:text-sm">
                    <thead>
                      <tr className="border-b border-line bg-surface-secondary text-ink-secondary">
                        <th scope="col" className="py-2.5 px-3 font-semibold">Ký hiệu</th>
                        <th scope="col" className="py-2.5 px-3 font-semibold">Tên chỉ tiêu (tiếng Việt)</th>
                        <th scope="col" className="py-2.5 px-3 text-center font-semibold">Đơn vị</th>
                        <th scope="col" className="py-2.5 px-3 font-semibold">Nhóm chỉ tiêu</th>
                        <th scope="col" className="py-2.5 px-3 font-semibold">Chiều hướng</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {capabilities.metrics.map((metric) => (
                        <tr key={metric.id} className="hover:bg-surface-hover/50">
                          <td className="py-2.5 px-3 font-bold text-ink">{metric.acronym || metric.id}</td>
                          <td className="py-2.5 px-3 font-medium text-ink">{metric.label}</td>
                          <td className="py-2.5 px-3 text-center font-mono text-xs font-semibold text-ink-secondary">{metric.unit || '%'}</td>
                          <td className="py-2.5 px-3 text-ink-secondary">{metric.groupLabel || metric.group || 'Chung'}</td>
                          <td className="py-2.5 px-3 text-xs text-ink-secondary">{getDirectionLabel(metric.direction)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* Section 5: Nguồn và giới hạn */}
              <section className="rounded-md border border-line bg-surface-secondary p-5 text-sm" aria-labelledby="source-heading">
                <div className="flex items-center gap-2">
                  <FileText className="size-4 text-ink-secondary" aria-hidden="true" />
                  <h2 id="source-heading" className="font-bold text-ink">Nguồn và giới hạn</h2>
                </div>
                {capabilities.analysis_available === true ? (
                  <>
                    <p className="mt-2 text-ink-secondary">{capabilities.source || 'API chưa công bố nguồn dữ liệu chi tiết.'}</p>
                    <p className="mt-2 text-ink-secondary">
                      Phiên bản Gold: {capabilities.goldVersion || 'chưa công bố'} · Kiểm tra gần nhất: {capabilities.validationTimestamp || 'chưa công bố'}
                    </p>
                    <p className="mt-3 border-t border-line pt-3 text-ink-secondary">
                      Hiện chưa có quy trình nhập nguồn mới trong giao diện này; trang không nhận trực tiếp CSV hoặc PDF scan.
                    </p>
                  </>
                ) : (
                  <p className="mt-2 text-ink-secondary">
                    API chưa xác nhận snapshot có thể chạy. Nguồn, phiên bản dữ liệu và thời điểm kiểm định chưa được xác nhận.
                  </p>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </WorkspaceShell>
  );
}
