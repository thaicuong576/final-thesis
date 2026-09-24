import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowRight, Database, FileText } from 'lucide-react';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import { Button } from '@/components/ui/button';
import { useAnalysisCapabilities } from '@/features/create-analysis/hooks/useAnalysisCapabilities';
import { formatPeriodsSignature } from '@/features/analysis-composer/model/intentParser';

export function DataPage() {
  const capabilitiesQuery = useAnalysisCapabilities();

  useEffect(() => {
    const previousTitle = document.title;
    document.title = 'Dữ liệu phân tích · Phân tích tài chính';
    return () => { document.title = previousTitle; };
  }, []);

  const capabilities = capabilitiesQuery.data;
  const runnableCapabilities = new Set(
    capabilities?.analysis_available === true ? capabilities.implemented_capabilities ?? [] : []
  );
  const canRunPeerAnalysis = runnableCapabilities.has('peer');
  const canRunMacroAnalysis = runnableCapabilities.has('macro');

  return (
    <WorkspaceShell activeSection="data" context={<span className="text-xs font-bold text-ink">DỮ LIỆU PHÂN TÍCH</span>}>
      <div className="min-h-[calc(100vh-80px)] bg-workspace px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-[1120px] space-y-6">
          <header className="border-b border-line pb-5">
            <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">Dữ liệu phân tích</h1>
            <p className="mt-2 max-w-2xl text-sm text-ink-secondary">
              Catalog dưới đây do API công bố. Chỉ có thể chạy phân tích khi API xác nhận snapshot dữ liệu đã kiểm định và năng lực tương ứng.
            </p>
          </header>

          {capabilitiesQuery.isPending && (
            <div className="rounded-md border border-line bg-card p-5 text-sm text-ink-secondary" role="status">
              Đang tải phạm vi dữ liệu từ hệ thống…
            </div>
          )}

          {capabilitiesQuery.isError && (
            <div className="rounded-md border border-warning/40 bg-card p-5" role="alert">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden="true" />
                <div className="space-y-3">
                  <h2 className="text-sm font-bold text-ink">Không thể xác định dữ liệu đang hỗ trợ</h2>
                  <p className="text-sm text-ink-secondary">Không thể xác nhận phạm vi từ API. Hãy thử tải lại trước khi tạo phân tích.</p>
                  <Button type="button" variant="outline" onClick={() => void capabilitiesQuery.refetch()} className="border-line text-xs">
                    Thử tải lại
                  </Button>
                </div>
              </div>
            </div>
          )}

          {capabilities && (
            <>
              {capabilities.analysis_available !== true && (
                <div className="rounded-md border border-warning/40 bg-warning-soft/50 p-4" role="alert">
                  <h2 className="text-sm font-bold text-ink">Chưa thể chạy phân tích trên dữ liệu hiện tại</h2>
                  <p className="mt-1 text-sm text-ink-secondary">
                    API chưa xác nhận snapshot đã kiểm định có thể chạy. Catalog vẫn hiển thị để tham khảo; trạng thái kho dữ liệu: {capabilities.database_status || 'chưa được API công bố'}.
                  </p>
                </div>
              )}

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
                  <Button asChild className="h-9 border border-amber-border bg-amber px-3 text-xs font-semibold text-ink hover:bg-amber-hover">
                    <Link to="/analysis">Tạo phân tích <ArrowRight className="ml-1 size-3.5" aria-hidden="true" /></Link>
                  </Button>
                </div>

                <dl className="grid gap-4 py-5 text-sm sm:grid-cols-3">
                  <div><dt className="text-xs text-ink-secondary">Ngân hàng</dt><dd className="mt-1 font-semibold text-ink">{capabilities.entities.length}</dd></div>
                  <div><dt className="text-xs text-ink-secondary">Kỳ dữ liệu</dt><dd className="mt-1 font-semibold text-ink">{formatPeriodsSignature(capabilities.periods) || 'Chưa công bố'}</dd></div>
                  <div><dt className="text-xs text-ink-secondary">Chỉ tiêu</dt><dd className="mt-1 font-semibold text-ink">{capabilities.metrics.length}</dd></div>
                  <div><dt className="text-xs text-ink-secondary">Phân tích khả dụng</dt><dd className="mt-1 font-semibold text-ink">{capabilities.analysis_available === true ? 'Có' : 'Chưa xác nhận'}</dd></div>
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
                    <p className="mt-2 text-ink">{canRunPeerAnalysis
                      ? capabilities.peerUniverse?.label || 'API chưa công bố nhóm tham chiếu'
                      : 'API chưa xác nhận phân tích nhóm tham chiếu có thể chạy.'}</p>
                    {canRunPeerAnalysis && capabilities.peerUniverse?.description && <p className="mt-1 text-xs text-ink-secondary">{capabilities.peerUniverse.description}</p>}
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Bối cảnh vĩ mô</h3>
                    <p className="mt-2 text-ink">{canRunMacroAnalysis
                      ? capabilities.macro.summary
                      : 'API chưa xác nhận năng lực phân tích vĩ mô có thể chạy.'}</p>
                    {canRunMacroAnalysis && <p className="mt-1 text-xs text-ink-secondary">{capabilities.macro.details}</p>}
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wide text-ink-secondary">Năng lực API xác nhận</h3>
                    <p className="mt-2 text-ink">{capabilities.implemented_capabilities?.length
                      ? capabilities.implemented_capabilities.join(' · ')
                      : 'Chưa công bố'}</p>
                    <p className="mt-1 text-xs text-ink-secondary">Trạng thái kho dữ liệu: {capabilities.database_status || 'chưa được API công bố'}</p>
                  </div>
                </div>
              </section>

              <section className="rounded-md border border-line bg-surface-secondary p-5 text-sm" aria-labelledby="source-heading">
                <div className="flex items-center gap-2">
                  <FileText className="size-4 text-ink-secondary" aria-hidden="true" />
                  <h2 id="source-heading" className="font-bold text-ink">Nguồn và giới hạn</h2>
                </div>
                {capabilities.analysis_available === true ? (
                  <>
                    <p className="mt-2 text-ink-secondary">{capabilities.source || 'API chưa công bố nguồn dữ liệu chi tiết.'}</p>
                    <p className="mt-2 text-ink-secondary">Phiên bản Gold: {capabilities.goldVersion || 'chưa công bố'} · Kiểm tra gần nhất: {capabilities.validationTimestamp || 'chưa công bố'}</p>
                    <p className="mt-3 border-t border-line pt-3 text-ink-secondary">Hiện chưa có quy trình nhập nguồn mới trong giao diện này; trang không nhận trực tiếp CSV hoặc PDF scan.</p>
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
