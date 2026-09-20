import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, RotateCcw, LayoutDashboard } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';

export interface ReportErrorFallbackProps {
  errorMessage?: string;
  errorDetail?: string;
  onRetry?: () => void;
}

export function ReportErrorFallback({
  errorMessage = 'Đã xảy ra sự cố trong quá trình kết xuất dữ liệu chỉ tiêu tài chính của báo cáo.',
  errorDetail,
  onRetry
}: ReportErrorFallbackProps) {
  return (
    <WorkspaceShell
      activeSection="reports"
      context={
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="font-bold text-ink">BÁO CÁO PHÂN TÍCH</span>
          <span className="text-border-strong">/</span>
          <span className="font-semibold text-danger">LỖI KẾT XUẤT</span>
        </div>
      }
    >
      <div className="mx-auto max-w-[800px] px-4 py-12 sm:px-6">
        <div className="rounded-lg border border-line bg-card p-6 shadow-sm space-y-5">
          <div className="flex items-start gap-4">
            <div className="grid size-10 shrink-0 place-items-center rounded-lg border border-danger/40 bg-danger-soft text-danger">
              <AlertTriangle className="size-5" aria-hidden="true" />
            </div>
            <div className="space-y-1">
              <h1 className="text-base font-bold text-ink">
                Không thể kết xuất báo cáo phân tích
              </h1>
              <p className="text-xs text-ink-secondary leading-relaxed">
                {errorMessage}
              </p>
            </div>
          </div>

          {errorDetail && (
            <div className="rounded-md border border-line bg-surface-secondary p-3">
              <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-ink-tertiary block mb-1">
                Chi tiết sự cố
              </span>
              <p className="text-xs font-mono text-ink-secondary break-all">
                {errorDetail}
              </p>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-line">
            <Button
              asChild
              size="sm"
              className="h-8 px-3 text-xs font-semibold gap-1.5 bg-amber text-ink border border-amber-border hover:bg-amber-hover shadow-xs"
            >
              <Link to="/reports">
                <ArrowLeft className="size-3.5" aria-hidden="true" />
                <span>Thư viện báo cáo</span>
              </Link>
            </Button>

            <Button
              asChild
              variant="outline"
              size="sm"
              className="h-8 px-3 text-xs font-semibold gap-1.5 border-line bg-surface-secondary text-ink hover:bg-surface-hover"
            >
              <Link to="/analysis">
                <LayoutDashboard className="size-3.5 text-ink-secondary" aria-hidden="true" />
                <span>Bàn làm việc phân tích</span>
              </Link>
            </Button>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onRetry ?? (() => window.location.reload())}
              className="h-8 px-3 text-xs font-semibold gap-1.5 border-line bg-surface-secondary text-ink hover:bg-surface-hover"
            >
              <RotateCcw className="size-3.5 text-ink-secondary" aria-hidden="true" />
              <span>Thử tải lại</span>
            </Button>
          </div>
        </div>
      </div>
    </WorkspaceShell>
  );
}
