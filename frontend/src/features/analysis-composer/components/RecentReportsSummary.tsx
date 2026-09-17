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
    <div className="border border-line bg-white rounded-lg p-4 space-y-3 shadow-surface">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
          Báo cáo gần đây
        </h3>
        <Link
          to="/reports"
          className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#1c5d9c] hover:underline"
        >
          <span>Xem thư viện</span>
          <ArrowUpRight className="w-3 h-3" />
        </Link>
      </div>

      <div className="space-y-2">
        {RECENT_REPORTS.map((report) => (
          <div
            key={report.id}
            className="p-3 rounded-md border border-line bg-white hover:bg-[#fcfbf9] transition flex items-center justify-between gap-3 text-xs"
          >
            <div className="min-w-0 space-y-0.5">
              <div className="font-semibold text-ink truncate">{report.title}</div>
              <div className="text-[11px] text-muted truncate">
                {report.scope} • {report.date}
              </div>
            </div>
            <Badge
              variant="outline"
              className="bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3] text-[10px] shrink-0 font-medium"
            >
              {report.status}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}
