import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowRight, Database, FileText, Loader2 } from 'lucide-react';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import { PageCrumbs } from '@/components/layout/PageCrumbs';
import { Button } from '@/components/ui/button';
import { useAnalysisCapabilities } from '@/features/create-analysis/hooks/useAnalysisCapabilities';
import { formatPeriodsSignature } from '@/features/analysis-composer/model/intentParser';
import type { Entity, Metric, PeerUniverse } from '@/entities/capability/model/types';

function getDirectionLabel(direction?: string): string {
  if (direction === 'higher_is_better') return 'Càng cao càng tốt';
  if (direction === 'lower_is_better') return 'Càng thấp càng tốt';
  if (direction === 'neutral') return 'Trung tính';
  return 'Theo dõi';
}

function isDistinctName(name?: string, ticker?: string): boolean {
  if (!name || !name.trim()) return false;
  if (!ticker || !ticker.trim()) return true;
  return name.trim().toUpperCase() !== ticker.trim().toUpperCase();
}

function formatEntityCatalogEntry(entity: Entity): string {
  return isDistinctName(entity.name, entity.ticker)
    ? `${entity.ticker} (${entity.name})`
    : entity.ticker;
}

function formatMetricSymbol(metric: Metric): string {
  if (metric.acronym === 'LLR_COVERAGE') return 'LLR';
  if (metric.acronym === 'NPL_G35') return 'NPL';
  if (metric.acronym) {
    return metric.acronym.replace(/_COVERAGE$/, '').replace(/_G\d+$/, '');
  }
  return metric.shortLabel || metric.id || '';
}

function formatCapabilityName(capability: string): string {
  switch (capability.toLowerCase()) {
    case 'company':
      return 'Doanh nghiệp';
    case 'sector':
      return 'Nhóm ngành';
    case 'macro':
      return 'Vĩ mô';
    default:
      return capability;
  }
}

function formatPeerUniverseLabel(peerUniverse?: PeerUniverse | null): string {
  if (!peerUniverse) return 'API chưa công bố nhóm tham chiếu';
  const entityCount = peerUniverse.entityIds?.length ?? 0;
  if (entityCount > 0) {
    return `${entityCount} ngân hàng: ${peerUniverse.entityIds.join(', ')}`;
  }
  return peerUniverse.label || 'API chưa công bố nhóm tham chiếu';
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

  return (
    <WorkspaceShell activeSection="data" context={<PageCrumbs items={[{ label: 'Dữ liệu' }]} />}>
      <div className="min-h-[calc(100vh-80px)] w-full max-w-full min-w-0 overflow-x-hidden bg-workspace px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-[1120px] min-w-0 space-y-6">
          <header className="border-b border-line pb-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">Dữ liệu phân tích</h1>
                <p className="mt-1 max-w-2xl text-sm text-ink-secondary break-words">
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
              <Loader2 className="size-4 animate-spin text-ink-secondary shrink-0" aria-hidden="true" />
              <span>Đang tải phạm vi dữ liệu từ hệ thống…</span>
            </div>
          )}

          {capabilitiesQuery.isError && (
            <div className="rounded-md border border-warning/40 bg-card p-5" role="alert">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden="true" />
                <div className="space-y-3 min-w-0 flex-1">
                  <h2 className="text-sm font-bold text-ink">Không thể xác định dữ liệu đang hỗ trợ</h2>
                  <p className="text-sm text-ink-secondary break-words">
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
              <p className="mx-auto mt-1 max-w-md text-sm text-ink-secondary break-words">
                API hiện chưa công bố dữ liệu hoặc snapshot đã kiểm định nào. Hãy kiểm tra kết nối với kho dữ liệu.
              </p>
            </div>
          )}

          {capabilities && !capabilitiesQuery.isError && !isEmpty && (
            <>
              {capabilities.analysis_available !== true && (
                <div className="rounded-md border border-warning/40 bg-warning-soft/50 p-4" role="alert">
                  <h2 className="text-sm font-bold text-ink">Chưa thể chạy phân tích trên dữ liệu hiện tại</h2>
                  <p className="mt-1 text-sm text-ink-secondary break-words">
                    API chưa xác nhận snapshot đã kiểm định có thể chạy. Catalog vẫn hiển thị để tham khảo; trạng thái kho dữ liệu: {capabilities.database_status || 'chưa được API công bố'}.
                  </p>
                </div>
              )}

              {/* Section 1: Catalog & Snapshot Overview */}
              <section className="w-full min-w-0 rounded-md border border-line bg-card p-4 sm:p-6" aria-labelledby="dataset-heading">
                <div className="border-b border-line pb-4">
                  <div className="flex items-center gap-2">
                    <Database className="size-4 text-ink-secondary shrink-0" aria-hidden="true" />
                    <h2 id="dataset-heading" className="text-base font-bold text-ink">Catalog năng lực API</h2>
                  </div>
                  <p className="mt-2 font-mono text-xs text-ink-secondary break-all">
                    {capabilities.dataset_snapshot_id
                      ? `Snapshot đã kiểm định: ${capabilities.dataset_snapshot_id}`
                      : `Mã catalog: ${capabilities.snapshotId || 'chưa công bố'} · Snapshot đã kiểm định: chưa công bố`}
                  </p>
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
                  <div className="min-w-0">
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Ngân hàng trong catalog</h3>
                    <p className="mt-2 leading-relaxed text-ink break-words">
                      {capabilities.entities.map(formatEntityCatalogEntry).join(' · ') || 'Chưa công bố'}
                    </p>
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Chỉ tiêu trong catalog</h3>
                    <p className="mt-2 leading-relaxed text-ink break-words">
                      {capabilities.metrics.map(formatMetricSymbol).join(' · ') || 'Chưa công bố'}
                    </p>
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Nhóm tham chiếu</h3>
                    <p className="mt-2 text-ink break-words">
                      {canRunPeerAnalysis
                        ? formatPeerUniverseLabel(capabilities.peerUniverse)
                        : 'API chưa xác nhận phân tích nhóm tham chiếu có thể chạy.'}
                    </p>
                    {canRunPeerAnalysis && capabilities.peerUniverse?.description && (
                      <p className="mt-1 text-xs text-ink-secondary break-words">{capabilities.peerUniverse.description}</p>
                    )}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Bối cảnh vĩ mô</h3>
                    <p className="mt-2 text-ink break-words">
                      {canRunMacroAnalysis
                        ? capabilities.macro.summary
                        : 'API chưa xác nhận năng lực phân tích vĩ mô có thể chạy.'}
                    </p>
                    {canRunMacroAnalysis && <p className="mt-1 text-xs text-ink-secondary break-words">{capabilities.macro.details}</p>}
                  </div>
                  <div className="min-w-0 sm:col-span-2">
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Năng lực API xác nhận</h3>
                    <p className="mt-2 text-ink break-words">
                      {capabilities.implemented_capabilities?.length
                        ? capabilities.implemented_capabilities.map(formatCapabilityName).join(' · ')
                        : 'Chưa công bố'}
                    </p>
                    <p className="mt-1 text-xs text-ink-secondary break-words">Trạng thái kho dữ liệu: {capabilities.database_status || 'chưa được API công bố'}</p>
                  </div>
                </div>

                <div className="mt-5 border-t border-line pt-3">
                  <p className="text-xs text-ink-secondary">
                    Ghi chú: Ô thiếu số liệu đã kiểm định sẽ được ghi rõ trong từng báo cáo.
                  </p>
                </div>
              </section>

              {/* Section 2: Danh mục chỉ tiêu tài chính */}
              <section className="w-full min-w-0 rounded-md border border-line bg-card p-4 sm:p-6" aria-labelledby="metrics-heading">
                <div className="border-b border-line pb-3">
                  <h2 id="metrics-heading" className="text-base font-bold text-ink">Chỉ tiêu tài chính ({capabilities.metrics.length})</h2>
                  <p className="mt-1 text-xs text-ink-secondary">Các chỉ số được định nghĩa theo chuẩn tài chính, có nhãn tiếng Việt và đơn vị đo rõ ràng.</p>
                </div>
                <div className="mt-4 w-full max-w-full min-w-0 overflow-x-auto rounded border border-line">
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
                          <td className="py-2.5 px-3 font-bold text-ink">{formatMetricSymbol(metric)}</td>
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

              {/* Section 3: Nguồn và giới hạn */}
              <section className="w-full min-w-0 rounded-md border border-line bg-surface-secondary p-4 sm:p-5 text-sm" aria-labelledby="source-heading">
                <div className="flex items-center gap-2">
                  <FileText className="size-4 text-ink-secondary shrink-0" aria-hidden="true" />
                  <h2 id="source-heading" className="font-bold text-ink">Nguồn và giới hạn</h2>
                </div>
                {capabilities.analysis_available === true ? (
                  <>
                    <p className="mt-2 text-ink-secondary break-words">{capabilities.source || 'API chưa công bố nguồn dữ liệu chi tiết.'}</p>
                    <p className="mt-2 text-ink-secondary break-words">
                      Phiên bản Gold: {capabilities.goldVersion || 'chưa công bố'} · Kiểm tra gần nhất: {capabilities.validationTimestamp || 'chưa công bố'}
                    </p>
                    <p className="mt-3 border-t border-line pt-3 text-ink-secondary break-words">
                      Hiện chưa có quy trình nhập nguồn mới trong giao diện này; trang không nhận trực tiếp CSV hoặc PDF scan.
                    </p>
                  </>
                ) : (
                  <p className="mt-2 text-ink-secondary break-words">
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
