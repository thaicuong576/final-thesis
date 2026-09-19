import { Link } from 'react-router-dom';
import { ArrowLeft, FileText, Filter, Plus, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';

export function ReportsPlaceholderPage() {
  return (
    <WorkspaceShell
      activeSection="reports"
      context={
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2 text-xs text-ink-secondary font-mono">
            <span>KHÔNG GIAN</span>
            <span className="text-border-strong">/</span>
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
        <div className="mx-auto max-w-[1120px] space-y-4">
          {/* Section 14.1 Header Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-line pb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-ink-secondary">
                  Lưu trữ kết quả phân tích
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-secondary text-ink-secondary border border-border">
                  VERIFIED RUNS
                </span>
              </div>
              <h1 className="text-xl font-bold tracking-tight text-ink">Thư viện báo cáo</h1>
              <p className="text-xs text-ink-secondary leading-relaxed">
                Tập hợp các báo cáo phân tích tài chính có nguồn gốc bằng chứng, số liệu kiểm chứng và lập luận chuyên gia.
              </p>
            </div>

            <Button asChild className="h-9 px-4 text-xs font-semibold gap-1.5 self-start sm:self-center shrink-0">
              <Link to="/analysis">
                <Plus className="size-3.5" aria-hidden="true" />
                <span>Tạo phân tích mới</span>
              </Link>
            </Button>
          </div>

          {/* Section 14.1 Search & Filter Toolbar */}
          <div className="border border-line bg-card rounded-md p-3 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 flex-1 max-w-md border border-line rounded-md bg-surface-secondary px-2.5 py-1.5 focus-within:border-border-focus focus-within:bg-card">
              <Search className="size-3.5 text-ink-tertiary shrink-0" aria-hidden="true" />
              <input
                type="text"
                placeholder="Tìm kiếm báo cáo theo mã CK, tiêu đề..."
                className="w-full bg-transparent border-0 p-0 text-xs text-ink placeholder:text-ink-tertiary focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-2 text-ink-secondary">
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 border border-line rounded-md bg-surface-secondary text-xs">
                <Filter className="size-3 text-ink-tertiary" />
                <span className="font-mono text-[11px]">Tất cả chu kỳ</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 border border-line rounded-md bg-surface-secondary text-xs">
                <span className="font-mono text-[11px]">Toàn bộ ngân hàng</span>
              </div>
              <span className="ml-auto font-mono text-[11px] text-ink-tertiary pl-2">
                0 BÁO CÁO
              </span>
            </div>
          </div>

          {/* Section 14.1 Data Container with Section 12.36 Integrated Empty State */}
          <div className="border border-line bg-card rounded-md overflow-hidden">
            {/* Table Column Headers */}
            <div className="grid grid-cols-12 gap-2 px-4 py-2.5 border-b border-line bg-surface-secondary text-[11px] font-mono font-bold uppercase tracking-wider text-ink-secondary">
              <div className="col-span-3">Mã báo cáo</div>
              <div className="col-span-4">Tiêu đề & Phạm vi</div>
              <div className="col-span-2">Chu kỳ dữ liệu</div>
              <div className="col-span-2">Thời điểm tạo</div>
              <div className="col-span-1 text-right">Trạng thái</div>
            </div>

            {/* Table Body Empty State */}
            <div className="py-16 px-4 text-center">
              <div className="grid size-12 place-items-center rounded-md border border-border bg-surface-secondary mx-auto mb-3 text-ink-tertiary">
                <FileText className="size-6 stroke-[1.8]" aria-hidden="true" />
              </div>
              <h2 className="text-sm font-bold text-ink mb-1">
                Chưa có báo cáo nào được tạo
              </h2>
              <p className="text-xs text-ink-secondary max-w-md mx-auto mb-5 leading-relaxed">
                Bắt đầu một phiên phân tích từ bàn làm việc để tạo báo cáo kiểm định đầu tiên có trích dẫn tài liệu và chỉ tiêu chi tiết.
              </p>
              <Button asChild className="h-9 px-4 text-xs font-semibold gap-1.5">
                <Link to="/analysis">
                  <ArrowLeft className="size-3.5" aria-hidden="true" />
                  <span>Đến Bàn làm việc phân tích</span>
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </WorkspaceShell>
  );
}
