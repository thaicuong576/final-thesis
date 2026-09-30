import type { ReactNode } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { BarChart3, Database, FileText, MessageSquareText } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
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
      <Sidebar collapsible="icon" className="border-r border-border-subtle bg-surface-secondary print:hidden">
        <SidebarHeader className="min-h-[64px] justify-center px-4 py-3 bg-surface-secondary group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:py-3">
          <Link to="/analysis" className="group flex items-center gap-3 text-ink group-data-[collapsible=icon]:justify-center">
            <span
              className="grid size-8 shrink-0 place-items-center rounded-lg bg-ink text-amber transition-colors group-hover:bg-[#3a3a36]"
              aria-hidden="true"
            >
              <BarChart3 className="size-[18px] stroke-[2.2]" />
            </span>
            <div className="flex min-w-0 flex-col group-data-[collapsible=icon]:hidden">
              <span className="truncate text-[15px] font-semibold leading-tight tracking-[-0.01em] text-ink">
                Phân tích tài chính
              </span>
              <span className="truncate text-xs text-ink-tertiary">Ngân hàng niêm yết Việt Nam</span>
            </div>
          </Link>
        </SidebarHeader>

        <SidebarContent className="bg-surface-secondary">
          <SidebarGroup className="p-3 pt-3 group-data-[collapsible=icon]:p-2 group-data-[collapsible=icon]:pt-3">
            <SidebarMenu className="gap-1">
              <WorkspaceNavItem to="/analysis" label="Phân tích mới" icon={MessageSquareText} active={activeSection === 'analysis'} />
              <WorkspaceNavItem to="/reports" label="Thư viện báo cáo" icon={FileText} active={activeSection === 'reports'} />
              <WorkspaceNavItem to="/data" label="Dữ liệu" icon={Database} active={activeSection === 'data'} />
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter className="border-t border-border-subtle bg-surface-secondary p-0">
          <div className="flex items-center gap-3 px-4 py-3 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
            <span
              className="grid size-8 shrink-0 place-items-center rounded-full bg-surface-selected text-[11px] font-semibold text-ink"
              title="Phùng Thái Cường"
            >
              PC
            </span>
            <div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
              <p className="truncate text-[13px] font-medium text-ink">Phùng Thái Cường</p>
              <p className="truncate text-xs text-ink-tertiary">Chuyên viên phân tích</p>
            </div>
          </div>
        </SidebarFooter>

        <SidebarRail />
      </Sidebar>

      <SidebarInset className="min-h-screen bg-workspace">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border-subtle bg-surface-primary/95 px-4 backdrop-blur-sm sm:px-6 print:hidden">
          <SidebarTrigger aria-label="Đóng/mở thanh điều hướng" className="-ml-1 text-ink-secondary" />
          <Separator orientation="vertical" className="h-5 bg-border-subtle" />
          <div className="min-w-0 flex-1">
            {context ?? <span className="text-[13px] font-semibold text-ink">Phân tích mới</span>}
          </div>
        </header>

        <main className="min-w-0 flex-1">{children}</main>
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
        className="h-10 px-3 text-[14px] font-medium text-ink-secondary transition-colors hover:bg-surface-hover hover:text-ink data-[active=true]:bg-surface-primary data-[active=true]:font-semibold data-[active=true]:text-ink data-[active=true]:shadow-[0_1px_2px_rgba(32,32,30,0.08)] data-[active=true]:ring-1 data-[active=true]:ring-border-subtle group-data-[collapsible=icon]:!size-9 group-data-[collapsible=icon]:!p-0 group-data-[collapsible=icon]:justify-center"
      >
        <NavLink to={to} aria-current={isCurrent ? 'page' : undefined} title={label}>
          <Icon
            className={`size-[18px] shrink-0 stroke-[1.8] ${isCurrent ? 'text-amber-active' : ''}`}
            aria-hidden="true"
          />
          <span className="truncate group-data-[collapsible=icon]:hidden">{label}</span>
        </NavLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}
