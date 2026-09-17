import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { ArrowUpRight } from 'lucide-react';

const RECENT_REPORTS = [
  {
    id: 'report-2026-09-10-1',
    title: 'Đánh giá hiệu quả sinh lời ngành Ngân hàng 2024',
    scope: 'ACB · TCB · VPB · Q1–Q4/2024',
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
    <div className="border border-line bg-card rounded-md p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] font-mono font-bold uppercase tracking-wider text-ink-secondary">
          Báo cáo gần đây
        </h3>
        <Link
          to="/reports"
          className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-amber-border hover:text-amber-active underline underline-offset-2"
        >
          <span>XEM THƯ VIỆN</span>
          <ArrowUpRight className="w-3 h-3" />
        </Link>
      </div>

      <div className="space-y-2">
        {RECENT_REPORTS.map((report) => (
          <div
            key={report.id}
            className="p-2.5 rounded-md border border-border-subtle bg-surface-secondary hover:bg-surface-hover hover:border-border transition-colors flex items-center justify-between gap-3 text-xs"
          >
            <div className="min-w-0 space-y-0.5">
              <div className="font-bold text-ink truncate">{report.title}</div>
              <div className="text-[11px] font-mono text-ink-secondary truncate">
                {report.scope} • {report.date}
              </div>
            </div>
            <Badge
              variant="outline"
              className="bg-[#e4f4ea] text-[#2f9e62] border-[#2f9e62]/30 text-[10px] shrink-0 font-semibold"
            >
              {report.status}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}
