import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  CheckCircle2,
  FileCheck2,
  Filter,
  Layers,
  Plus,
  Search,
  Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import { SAMPLE_REPORTS } from '@/features/analysis-report';

export function ReportsListPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [tickerFilter, setTickerFilter] = useState('all');

  const filteredReports = useMemo(() => {
    return SAMPLE_REPORTS.filter((item) => {
      const matchSearch =
        searchTerm === '' ||
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.query.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.targetTicker.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.peerTickers.some((p) => p.toLowerCase().includes(searchTerm.toLowerCase()));

      const matchTicker =
        tickerFilter === 'all' ||
        item.targetTicker === tickerFilter ||
        item.peerTickers.includes(tickerFilter);

      return matchSearch && matchTicker;
    });
  }, [searchTerm, tickerFilter]);

  return (
    <WorkspaceShell
      activeSection="reports"
      context={
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="font-bold text-ink">THƯ VIỆN BÁO CÁO</span>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-xs text-ink-secondary font-mono">
            <span className="w-2 h-2 rounded-full bg-ready" aria-hidden="true" />
            <span>KHO LƯU TRỮ HOẠT ĐỘNG</span>
          </div>
        </div>
      }
    >
      <div className="min-h-[calc(100vh-80px)] bg-workspace py-5 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-[1180px] space-y-5">
          {/* Header Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-line pb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-ink-secondary">
                  Lưu trữ kết quả phân tích
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-secondary text-ink-secondary border border-border">
                  3 MẪU BÁO CÁO SẴN CÓ
                </span>
              </div>
              <h1 className="text-xl font-bold tracking-tight text-ink">Thư viện báo cáo</h1>
              <p className="text-xs text-ink-secondary leading-relaxed max-w-2xl">
                Tập hợp các báo cáo phân tích tài chính có nguồn gốc bằng chứng, số liệu kiểm chứng và lập luận chuyên gia. Bấm vào bất kỳ mẫu báo cáo nào dưới đây để xem chi tiết.
              </p>
            </div>

            <Button asChild className="h-9 px-4 text-xs font-semibold gap-1.5 self-start sm:self-center shrink-0 bg-amber text-ink border border-amber-border hover:bg-amber-hover">
              <Link to="/analysis">
                <Plus className="size-3.5" aria-hidden="true" />
                <span>Tạo phân tích mới</span>
              </Link>
            </Button>
          </div>

          {/* Quick Highlight Cards for 3 Samples */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
            {SAMPLE_REPORTS.map((sample, idx) => (
              <Link
                key={sample.id}
                to={`/reports/${sample.slug}`}
                className="group border border-line bg-card rounded-lg p-4 space-y-2.5 hover:border-amber-border hover:shadow-sm transition-all"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-amber-border bg-amber-soft/50 px-2 py-0.5 rounded border border-amber-border/50">
                    Mẫu 0{idx + 1}
                  </span>
                  <div className="flex items-center gap-1 text-[11px] font-mono text-[#1b4332] bg-[#e8f5ee] px-1.5 py-0.5 rounded border border-[#a3cfbb]">
                    <CheckCircle2 className="size-3 text-[#2d6a4f]" aria-hidden="true" />
                    <span>{sample.hasRevision ? 'Đã hiệu đính' : 'Kiểm định: Đạt'}</span>
                  </div>
                </div>

                <div>
                  <h2 className="text-xs font-bold text-ink group-hover:text-amber-border transition-colors leading-snug">
                    {sample.name}
                  </h2>
                  <p className="text-[11px] text-ink-secondary line-clamp-2 mt-1 leading-relaxed">
                    {sample.query}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-1 border-t border-line/60 text-[11px] font-mono">
                  <span className="text-ink-tertiary">{sample.scopeBadge}</span>
                  <span className="inline-flex items-center gap-1 font-semibold text-amber-border group-hover:translate-x-0.5 transition-transform">
                    <span>Xem báo cáo</span>
                    <ArrowRight className="size-3" aria-hidden="true" />
                  </span>
                </div>
              </Link>
            ))}
          </div>

          {/* Search & Filter Toolbar */}
          <div className="border border-line bg-card rounded-md p-3 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 flex-1 max-w-md border border-line rounded-md bg-surface-secondary px-2.5 py-1.5 focus-within:border-border-focus focus-within:bg-card">
              <Search className="size-3.5 text-ink-tertiary shrink-0" aria-hidden="true" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Tìm kiếm báo cáo theo mã CK, tiêu đề..."
                className="w-full bg-transparent border-0 p-0 text-xs text-ink placeholder:text-ink-tertiary focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-2 text-ink-secondary">
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 border border-line rounded-md bg-surface-secondary text-xs">
                <Filter className="size-3 text-ink-tertiary" />
                <select
                  value={tickerFilter}
                  onChange={(e) => setTickerFilter(e.target.value)}
                  className="bg-transparent border-0 p-0 font-mono text-[11px] text-ink focus:outline-none"
                >
                  <option value="all">Toàn bộ ngân hàng</option>
                  <option value="ACB">ACB</option>
                  <option value="TCB">TCB</option>
                  <option value="MBB">MBB</option>
                </select>
              </div>

              <span className="ml-auto font-mono text-[11px] text-ink-tertiary pl-2">
                {filteredReports.length} BÁO CÁO
              </span>
            </div>
          </div>

          {/* Table Container */}
          <div className="border border-line bg-card rounded-md overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-line bg-surface-secondary text-[11px] font-mono font-bold uppercase tracking-wider text-ink-secondary">
                    <th className="py-2.5 px-4">Mẫu báo cáo</th>
                    <th className="py-2.5 px-4">Tiêu đề phân tích & Phạm vi</th>
                    <th className="py-2.5 px-4">Chu kỳ dữ liệu</th>
                    <th className="py-2.5 px-4">Năng lực kích hoạt</th>
                    <th className="py-2.5 px-4 text-center">Trạng thái</th>
                    <th className="py-2.5 px-4 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {filteredReports.length > 0 ? (
                    filteredReports.map((sample) => (
                      <tr
                        key={sample.id}
                        className="hover:bg-surface-hover transition-colors group"
                      >
                        <td className="py-3 px-4 align-top whitespace-nowrap">
                          <Link
                            to={`/reports/${sample.slug}`}
                            className="font-mono font-bold text-ink group-hover:text-amber-border transition-colors block"
                          >
                            {sample.name}
                          </Link>
                          <span className="text-[10px] font-mono text-ink-tertiary block mt-0.5">
                            ID: {sample.slug}
                          </span>
                        </td>

                        <td className="py-3 px-4 align-top max-w-md">
                          <Link
                            to={`/reports/${sample.slug}`}
                            className="font-semibold text-ink group-hover:text-amber-border transition-colors block leading-snug"
                          >
                            {sample.query}
                          </Link>
                          <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                            <Badge className="bg-amber text-ink border-amber-border text-[10px] font-bold font-mono px-1.5 py-0">
                              Mục tiêu: {sample.targetTicker}
                            </Badge>
                            {sample.peerTickers.map((p) => (
                              <Badge
                                key={p}
                                variant="outline"
                                className="bg-surface-secondary text-ink-secondary border-border font-mono text-[10px] px-1.5 py-0"
                              >
                                Đối chuẩn: {p}
                              </Badge>
                            ))}
                          </div>
                        </td>

                        <td className="py-3 px-4 align-top whitespace-nowrap font-mono text-ink-secondary">
                          <span>Niên độ {sample.period}</span>
                          <span className="block text-[10px] text-ink-tertiary mt-0.5">Dữ liệu Q4/2024</span>
                        </td>

                        <td className="py-3 px-4 align-top">
                          <div className="flex flex-wrap gap-1">
                            {sample.capabilities.map((cap) => (
                              <span
                                key={cap}
                                className="inline-flex items-center gap-1 text-[11px] font-medium text-ink bg-surface-secondary px-2 py-0.5 rounded border border-border"
                              >
                                <Layers className="size-2.5 text-ink-tertiary" />
                                <span>{cap}</span>
                              </span>
                            ))}
                          </div>
                        </td>

                        <td className="py-3 px-4 align-top text-center whitespace-nowrap">
                          {sample.hasRevision ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-amber-soft text-ink border border-amber-border/60">
                              <Sparkles className="size-3 text-amber-border" />
                              <span>Đã hiệu đính</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-[#e8f5ee] text-[#1b4332] border border-[#a3cfbb]">
                              <CheckCircle2 className="size-3 text-[#2d6a4f]" />
                              <span>Kiểm định: Đạt</span>
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-4 align-top text-right whitespace-nowrap">
                          <Button
                            asChild
                            variant="outline"
                            size="sm"
                            className="h-7 px-2.5 text-xs font-semibold gap-1 border-line bg-surface-secondary hover:bg-amber-soft hover:text-ink hover:border-amber-border"
                          >
                            <Link to={`/reports/${sample.slug}`}>
                              <FileCheck2 className="size-3 text-ink-secondary" />
                              <span>Xem báo cáo</span>
                            </Link>
                          </Button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-10 text-center text-xs text-ink-secondary">
                        Không tìm thấy báo cáo nào phù hợp với từ khóa tìm kiếm.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </WorkspaceShell>
  );
}
