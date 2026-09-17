import type { ReactNode } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { BarChart3, FileText, UserRound } from 'lucide-react';
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
  SidebarTrigger,
} from '@/components/ui/sidebar';

type WorkspaceSection = 'analysis' | 'reports';

interface WorkspaceShellProps {
  activeSection: WorkspaceSection;
  context?: ReactNode;
  children: ReactNode;
}

export function WorkspaceShell({ activeSection, context, children }: WorkspaceShellProps) {
  return (
    <SidebarProvider defaultOpen className="min-h-screen bg-workspace text-ink">
      <Sidebar collapsible="offcanvas" className="border-r border-line bg-surface-secondary">
        <SidebarHeader className="min-h-[64px] justify-center px-4 py-3 border-b border-line bg-surface-secondary">
          <Link to="/analysis" className="flex items-center gap-2.5 text-xs font-semibold tracking-[-0.01em] text-ink group">
            <span className="grid size-7 shrink-0 place-items-center rounded-md border border-amber-border bg-amber text-ink shadow-[0_1px_0_rgba(98,63,0,0.55)] transition group-hover:bg-amber-hover" aria-hidden="true">
              <BarChart3 className="size-4 stroke-[2.2]" />
            </span>
            <div className="flex flex-col min-w-0">
              <span className="font-bold text-[13px] text-ink leading-tight">Phân tích tài chính</span>
              <span className="text-[10px] font-mono text-ink-tertiary">STAGING · WORKBENCH</span>
            </div>
          </Link>
        </SidebarHeader>

        <SidebarContent className="bg-surface-secondary">
          <SidebarGroup className="p-3 pt-4">
            <SidebarMenu className="gap-1.5">
              <WorkspaceNavItem to="/analysis" label="Bàn làm việc phân tích" icon={BarChart3} active={activeSection === 'analysis'} />
              <WorkspaceNavItem to="/reports" label="Thư viện báo cáo" icon={FileText} active={activeSection === 'reports'} />
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter className="p-0 border-t border-line bg-surface-secondary">
          <div className="flex items-center gap-2.5 px-4 py-3">
            <span className="grid size-7 shrink-0 place-items-center rounded-md border border-border-strong bg-card text-[10px] font-mono font-bold text-ink">PTC</span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-ink">Phùng Thái Cường</p>
              <p className="truncate text-[10px] text-ink-tertiary font-mono">Chuyên viên phân tích</p>
            </div>
            <UserRound className="size-3.5 text-ink-tertiary" aria-hidden="true" />
          </div>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset className="min-h-screen bg-workspace">
        <div className="flex min-h-11 items-center gap-3 border-b border-line bg-card px-4 md:hidden">
          <SidebarTrigger aria-label="Mở điều hướng" className="-ml-1" />
          <span className="text-xs font-bold text-ink">Phân tích tài chính</span>
        </div>

        {context && <header className="border-b border-line bg-card">{context}</header>}

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
        size="default"
        className="h-9 px-3 text-xs font-medium text-ink transition-colors hover:bg-surface-hover data-[active=true]:bg-surface-selected data-[active=true]:font-semibold data-[active=true]:border-l-2 data-[active=true]:border-amber data-[active=true]:rounded-l-none"
      >
        <NavLink to={to} aria-current={isCurrent ? 'page' : undefined}>
          <Icon className="size-4 stroke-[1.8]" aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}
