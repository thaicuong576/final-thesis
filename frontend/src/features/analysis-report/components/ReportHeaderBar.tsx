import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  Check,
  Copy,
  Database,
  Download,
  Info
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { AnalysisReport } from '../model/types';
import { SAMPLE_REPORTS } from '../mock/mockReports';

interface ReportHeaderBarProps {
  report: AnalysisReport;
  isDemo?: boolean;
}

const REPORT_STATUS_LABELS: Record<NonNullable<AnalysisReport['status']>, string> = {
  completed: 'Hoàn tất',
  partial: 'Kết quả một phần',
  accepted_with_limitations: 'Chấp nhận có giới hạn',
  error: 'Lỗi'
};

export function ReportHeaderBar({ report, isDemo = false }: ReportHeaderBarProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyLink = () => {
    navigator.clipboard?.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportJson = () => {
    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(report, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${report.report_id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="sticky top-0 z-20 border-b border-line bg-card shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/95">
      <div className="mx-auto max-w-[1280px] px-4 py-3 sm:px-6 lg:px-8">
        {isDemo && (
          <div className="mb-3 flex items-start gap-2 rounded-md border border-warning/40 bg-warning-soft/60 p-3 text-xs text-ink" role="note">
            <Info className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden="true" />
            <p><strong>Mẫu minh họa, dữ liệu giả lập.</strong> Nội dung này không được lấy từ API và không phải kết quả phân tích thực tế.</p>
          </div>
        )}
        {!isDemo && report.status === 'partial' && (
          <div className="mb-3 rounded-md border border-warning/40 bg-warning-soft/60 p-3 text-xs text-ink" role="status">
            Kết quả một phần: API chưa công bố phản biện Stage 2 hoặc tóm tắt hiệu đính cho báo cáo này.
          </div>
        )}
        {/* Navigation, Quick Switcher & Quality Assurance Badges */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-2.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              asChild
              variant="outline"
              size="sm"
              className="h-8 px-2.5 text-xs font-semibold gap-1.5 border-line bg-surface-secondary text-ink hover:bg-surface-hover shrink-0"
            >
              <Link to="/reports">
                <ArrowLeft className="size-3.5 shrink-0" aria-hidden="true" />
                <span>Thư viện báo cáo</span>
              </Link>
            </Button>

            {isDemo && (
              <div className="flex items-center gap-1.5 overflow-x-auto" aria-label="Các mẫu minh họa">
                <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-ink-tertiary hidden md:inline-block">
                  Mẫu minh họa:
                </span>
                {SAMPLE_REPORTS.map((s) => {
                  const isActive = s.report.report_id === report.report_id;
                  return (
                    <Link
                      key={s.id}
                      to={`/reports/${s.slug}`}
                      className={`px-2.5 py-1 text-xs font-mono rounded transition-colors whitespace-nowrap ${
                        isActive
                          ? 'bg-amber text-ink font-bold border border-amber-border shadow-xs'
                          : 'bg-surface-secondary text-ink-secondary hover:text-ink hover:bg-surface-hover border border-border font-medium'
                      }`}
                    >
                      {s.shortName}
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {!isDemo && (
              <>
                <span className="inline-flex items-center gap-1.5 rounded border border-border bg-surface-secondary px-2 py-0.5 text-xs text-ink-secondary">
                  <Info className="size-3.5 text-ink-tertiary" aria-hidden="true" />
                  <span>Trạng thái API: {report.status ? REPORT_STATUS_LABELS[report.status] : 'chưa công bố'}</span>
                </span>
                {report.atomic_claims !== undefined && (
                  <span className="inline-flex items-center gap-1.5 rounded border border-border bg-surface-secondary px-2 py-0.5 text-xs text-ink-secondary">
                    <span>Stage 1: {report.atomic_claims.length === 0
                      ? 'không có nhận định'
                    : report.atomic_claims.some((claim) => claim.stage1_status === 'rejected')
                      ? 'có nhận định bị từ chối'
                      : report.atomic_claims.every((claim) => claim.stage1_status === 'accepted')
                        ? 'mọi nhận định được chấp nhận'
                        : 'chưa công bố trạng thái'}</span>
                  </span>
                )}
                {report.revision_summary && (
                  <span className="inline-flex items-center gap-1.5 rounded border border-border bg-surface-secondary px-2 py-0.5 text-xs text-ink-secondary">
                    <span>Phản biện: {report.revision_summary.status}</span>
                  </span>
                )}
              </>
            )}
            <span className="inline-flex items-center gap-1.5 rounded border border-border bg-surface-secondary px-2 py-0.5 text-xs font-mono text-ink-secondary">
              <Database className="size-3 text-ink-tertiary" aria-hidden="true" />
              <span>Snapshot: {report.analysis_plan?.dataset_snapshot_id || 'chưa được công bố'}</span>
            </span>
          </div>
        </div>

        {/* Report Title & Actions */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-3">
          <div className="space-y-1 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              {report.target_ticker && <Badge className="bg-amber text-ink border-amber-border hover:bg-amber text-xs font-bold font-mono px-2 py-0.5">
                Mục tiêu: {report.target_ticker}
              </Badge>}
              {(report.peer_tickers || []).map((peer) => (
                <Badge
                  key={peer}
                  variant="outline"
                  className="bg-surface-secondary text-ink-secondary border-border font-mono text-xs px-2 py-0.5"
                >
                  Đối chuẩn: {peer}
                </Badge>
              ))}
              {report.period && <span className="text-[11px] font-mono text-ink-tertiary">Niên độ {report.period}</span>}
            </div>

            <h1 className="text-base sm:text-lg font-bold tracking-tight text-ink leading-snug">
              {report.query || 'API không công bố nội dung truy vấn'}
            </h1>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-start md:self-auto">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCopyLink}
              className="h-8 px-2.5 text-xs font-medium gap-1.5 border-line bg-surface-secondary text-ink hover:bg-surface-hover"
            >
              {copied ? (
                <>
                  <Check className="size-3.5 text-[#2d6a4f]" aria-hidden="true" />
                  <span className="text-[#2d6a4f]">Đã sao chép</span>
                </>
              ) : (
                <>
                  <Copy className="size-3.5 text-ink-secondary" aria-hidden="true" />
                  <span>Sao chép liên kết</span>
                </>
              )}
            </Button>

            <Button
              type="button"
              size="sm"
              onClick={handleExportJson}
              className="h-8 px-3 text-xs font-semibold gap-1.5 bg-amber text-ink border border-amber-border hover:bg-amber-hover shadow-xs"
            >
              <Download className="size-3.5" aria-hidden="true" />
              <span>Xuất báo cáo</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
