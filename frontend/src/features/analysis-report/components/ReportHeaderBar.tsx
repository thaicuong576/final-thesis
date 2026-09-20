import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  Copy,
  Database,
  Download,
  ShieldCheck
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { AnalysisReport } from '../model/types';
import { SAMPLE_REPORTS } from '../mock/mockReports';

interface ReportHeaderBarProps {
  report: AnalysisReport;
}

export function ReportHeaderBar({ report }: ReportHeaderBarProps) {
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

            {/* Quick switcher for 3 sample reports */}
            <div className="flex items-center gap-1.5 overflow-x-auto">
              <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-ink-tertiary hidden md:inline-block">
                Xem nhanh:
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
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Stage 1 acceptance: Kiểm tra số học: Đạt */}
            <span className="inline-flex items-center gap-1.5 rounded border border-[#a3cfbb] bg-[#e8f5ee] px-2 py-0.5 text-xs font-medium text-[#1b4332]">
              <ShieldCheck className="size-3.5 text-[#2d6a4f]" aria-hidden="true" />
              <span>Kiểm tra số học: Đạt</span>
            </span>

            {/* Stage 2 acceptance: Phản biện logic: Đạt */}
            <span
              className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-medium ${
                report.revision_summary?.status === 'revised_and_passed'
                  ? 'border-amber-border/70 bg-amber-soft text-ink font-semibold'
                  : 'border-slate-300 bg-slate-100 text-slate-800'
              }`}
            >
              <CheckCircle2 className="size-3.5 text-slate-600" aria-hidden="true" />
              <span>
                {report.revision_summary?.status === 'revised_and_passed'
                  ? 'Phản biện logic: Đã hiệu đính'
                  : 'Phản biện logic: Đạt'}
              </span>
            </span>

            {/* Friendly Data Snapshot Label */}
            <span className="inline-flex items-center gap-1.5 rounded border border-border bg-surface-secondary px-2 py-0.5 text-xs font-mono text-ink-secondary">
              <Database className="size-3 text-ink-tertiary" aria-hidden="true" />
              <span>Dữ liệu Q4/2024</span>
            </span>
          </div>
        </div>

        {/* Report Title & Actions */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-3">
          <div className="space-y-1 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-amber text-ink border-amber-border hover:bg-amber text-xs font-bold font-mono px-2 py-0.5">
                Mục tiêu: {report.target_ticker}
              </Badge>
              {report.peer_tickers.map((peer) => (
                <Badge
                  key={peer}
                  variant="outline"
                  className="bg-surface-secondary text-ink-secondary border-border font-mono text-xs px-2 py-0.5"
                >
                  Đối chuẩn: {peer}
                </Badge>
              ))}
              <span className="text-[11px] font-mono text-ink-tertiary">
                Niên độ {report.period}
              </span>
            </div>

            <h1 className="text-base sm:text-lg font-bold tracking-tight text-ink leading-snug">
              {report.query}
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
