import type { ReactNode } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { BarChart3, Database, FileText, MessageSquareText } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { analyticalPeriodIds } from '@/entities/capability/model/coverage';
import { useAnalysisCapabilities } from '@/features/create-analysis/hooks/useAnalysisCapabilities';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from '@/components/ui/sidebar';

type WorkspaceSection = 'analysis' | 'data' | 'reports';

interface WorkspaceShellProps {
  activeSection: WorkspaceSection;
  context?: ReactNode;
  children: ReactNode;
}

export function WorkspaceShell({ activeSection, context, children }: WorkspaceShellProps) {
  return (
    <SidebarProvider defaultOpen className="min-h-screen bg-workspace text-ink">
      <Sidebar collapsible="icon" className="border-r-0 bg-sidebar text-sidebar-foreground print:hidden">
        <SidebarHeader className="min-h-[68px] justify-center border-b border-sidebar-border px-4 py-3 bg-sidebar group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:py-3">
          <Link to="/analysis" className="group flex items-center gap-3 text-ink group-data-[collapsible=icon]:justify-center">
            <span
              className="grid size-8 shrink-0 place-items-center rounded-lg bg-amber text-ink transition-colors group-hover:bg-amber-hover"
              aria-hidden="true"
            >
              <BarChart3 className="size-[18px] stroke-[2.2]" />
            </span>
            <div className="flex min-w-0 flex-col group-data-[collapsible=icon]:hidden">
              <span className="truncate text-[15px] font-semibold leading-tight text-white">
                Phân tích tài chính
              </span>
              <span className="truncate text-xs text-[#9c978c]">Ngân hàng niêm yết Việt Nam</span>
            </div>
          </Link>
        </SidebarHeader>

        <SidebarContent className="bg-sidebar">
          <SidebarGroup className="p-3 pt-3 group-data-[collapsible=icon]:p-2 group-data-[collapsible=icon]:pt-3">
            <SidebarMenu className="gap-1">
              <WorkspaceNavItem to="/analysis" label="Phân tích mới" icon={MessageSquareText} active={activeSection === 'analysis'} />
              <WorkspaceNavItem to="/reports" label="Thư viện báo cáo" icon={FileText} active={activeSection === 'reports'} />
              <WorkspaceNavItem to="/data" label="Dữ liệu" icon={Database} active={activeSection === 'data'} />
            </SidebarMenu>
          </SidebarGroup>
          <DatasetStatus />
        </SidebarContent>

        <SidebarFooter className="border-t border-sidebar-border bg-sidebar p-0">
          <div className="flex items-center gap-3 px-4 py-3 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
            <span
              className="grid size-8 shrink-0 place-items-center rounded-full bg-sidebar-accent text-[11px] font-semibold text-white"
              title="Phùng Thái Cường"
            >
              PC
            </span>
            <div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
              <p className="truncate text-[13px] font-medium text-white">Phùng Thái Cường</p>
              <p className="truncate text-xs text-[#8f8a7f]">Chuyên viên phân tích</p>
            </div>
          </div>
        </SidebarFooter>

        <SidebarRail />
      </Sidebar>

      <SidebarInset className="min-h-screen bg-workspace">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border-subtle bg-surface-primary/90 px-4 backdrop-blur-sm sm:px-6 print:hidden">
          <SidebarTrigger aria-label="Đóng/mở thanh điều hướng" className="-ml-1 text-ink-secondary" />
          <Separator orientation="vertical" className="h-5 bg-border-subtle" />
          <div className="min-w-0 flex-1">
            {context ?? <span className="text-[13px] font-semibold text-ink">Phân tích mới</span>}
          </div>
        </header>

        <main className="paper-grid min-w-0 flex-1">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}

function WorkspaceNavItem({ to, label, icon: Icon, active }: { to: string; label: string; icon: LucideIcon; active: boolean }) {
  const location = useLocation();
  const isCurrent = active || location.pathname === to;

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        asChild
        isActive={isCurrent}
        tooltip={label}
        size="default"
        className="h-10 px-3 text-[14px] font-medium text-[#bdb7ab] transition-colors hover:bg-sidebar-accent hover:text-white data-[active=true]:bg-sidebar-accent data-[active=true]:font-semibold data-[active=true]:text-white data-[active=true]:shadow-[inset_2px_0_0_var(--accent)] group-data-[collapsible=icon]:!size-9 group-data-[collapsible=icon]:!p-0 group-data-[collapsible=icon]:justify-center"
      >
        <NavLink to={to} aria-current={isCurrent ? 'page' : undefined} title={label}>
          <Icon
            className={`size-[18px] shrink-0 stroke-[1.8] ${isCurrent ? 'text-amber' : ''}`}
            aria-hidden="true"
          />
          <span className="truncate group-data-[collapsible=icon]:hidden">{label}</span>
        </NavLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}

/** Live summary of the dataset the API is serving; nothing here is hard-coded to one snapshot. */
function DatasetStatus() {
  const { data } = useAnalysisCapabilities();
  if (!data) return null;
  const tickers = (data.entities || []).map((e) => e.ticker || e.id);
  const periods = analyticalPeriodIds(data);
  const latest = periods[periods.length - 1];
  const years = Array.from(new Set(periods.map((p) => p.slice(0, 4)))).sort();
  const snapshot = data.dataset_snapshot_id || data.datasetSnapshotId || data.snapshotId || '';
  const label = snapshot.startsWith('gold') ? 'Bộ Gold v5 · đã đối chiếu BCTC' : 'BCTC hợp nhất · đã đối chiếu';
  const latestLabel = latest ? latest.replace(/^(\d{4})_Q(\d)$/, 'Q$2/$1') : '';
  return (
    <div className="mx-3 mt-auto mb-3 rounded-xl bg-sidebar-accent p-3 text-xs text-[#aaa497] group-data-[collapsible=icon]:hidden">
      <p className="m-0 flex items-center gap-2 font-semibold text-[#f1ece2]">
        <span className={`size-1.5 rounded-full ${data.analysis_available === false ? 'bg-amber' : 'bg-[#4cc38a]'}`} aria-hidden="true" />
        {label}
      </p>
      <p className="mt-1.5 mb-2 leading-relaxed">
        {tickers.length} ngân hàng · {years.length > 1 ? `${years[0]}–${years[years.length - 1]}` : years[0]}
        {latestLabel ? ` · mới nhất ${latestLabel}` : ''} · {(data.metrics || []).length} chỉ tiêu
      </p>
      <div className="flex flex-wrap gap-1">
        {tickers.map((t) => (
          <span key={t} className="rounded bg-[#1b1a18] px-1.5 py-px font-mono text-[10px] font-semibold text-[#e9e4da]">
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}
