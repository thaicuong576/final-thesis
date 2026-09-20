import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { ArrowUpRight, History } from 'lucide-react';

const RECENT_REPORTS = [
  {
    id: 'report-2026-09-10-1',
    title: 'Đánh giá hiệu quả sinh lời ngành Ngân hàng 2024',
    scope: 'ACB · TCB · VPB',
    date: '10/09/2026',
    status: 'Hoàn tất'
  },
  {
    id: 'report-2026-09-08-2',
    title: 'So sánh chất lượng nợ ACB vs MBB Q4/2024',
    scope: 'ACB · MBB · Q4/2024',
    date: '08/09/2026',
    status: 'Hoàn tất'
  }
];

export function RecentReportsSummary() {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-ink-secondary flex items-center gap-1.5">
          <History className="w-3.5 h-3.5 text-ink-secondary" />
          <span>Gần đây</span>
        </h3>
        <Link
          to="/reports"
          className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-border hover:text-amber-active underline underline-offset-2"
        >
          <span>Xem tất cả</span>
          <ArrowUpRight className="w-3 h-3" />
        </Link>
      </div>

      <div className="border border-line bg-card rounded-md divide-y divide-border-subtle overflow-hidden">
        {RECENT_REPORTS.map((report) => (
          <div
            key={report.id}
            className="p-3 hover:bg-surface-hover transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs group"
          >
            {/* Col 1 & 2: Report Title & Scope */}
            <div className="min-w-0 flex-1 space-y-0.5">
              <div className="font-semibold text-ink truncate group-hover:text-amber-border transition-colors">
                {report.title}
              </div>
              <div className="text-[11px] font-mono text-ink-secondary truncate">
                {report.scope}
              </div>
            </div>

            {/* Col 3 & 4: Date & Status & Action */}
            <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0 pt-1 sm:pt-0 border-t sm:border-t-0 border-border-subtle/50">
              <span className="text-[11px] font-mono text-ink-tertiary">
                {report.date}
              </span>
              <Badge
                variant="outline"
                className="bg-[#e4f4ea] text-[#2f9e62] border-[#2f9e62]/30 text-[10px] font-semibold px-2 py-0"
              >
                {report.status}
              </Badge>
              <Link
                to="/reports"
                className="text-[11px] font-medium text-ink-secondary hover:text-ink hover:underline shrink-0"
              >
                Mở lại
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
