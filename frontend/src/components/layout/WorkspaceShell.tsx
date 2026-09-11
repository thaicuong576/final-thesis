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
  SidebarSeparator,
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
    <SidebarProvider defaultOpen className="min-h-screen bg-background text-foreground">
      <Sidebar collapsible="offcanvas" className="border-sidebar-border bg-sidebar">
        <SidebarHeader className="min-h-[76px] justify-center px-5 py-4">
          <Link to="/analysis" className="flex items-center gap-3 text-sm font-semibold tracking-[-0.01em] text-ink">
            <span className="grid size-8 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground" aria-hidden="true">
              <BarChart3 data-icon="inline-start" />
            </span>
            <span>Phân tích tài chính</span>
          </Link>
        </SidebarHeader>

        <SidebarSeparator className="mx-0 w-full" />

        <SidebarContent>
          <SidebarGroup className="p-4 pt-6">
            <SidebarMenu>
              <WorkspaceNavItem to="/analysis" label="Phân tích" icon={BarChart3} active={activeSection === 'analysis'} />
              <WorkspaceNavItem to="/reports" label="Báo cáo" icon={FileText} active={activeSection === 'reports'} />
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter className="p-0">
          <SidebarSeparator className="mx-0 w-full" />
          <div className="flex items-center gap-3 px-5 py-5">
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-secondary text-[10px] font-semibold text-secondary-foreground">PTC</span>
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-ink">Phùng Thái Cường</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">Chuyên viên phân tích</p>
            </div>
            <UserRound className="ml-auto size-4 text-muted-foreground" aria-hidden="true" />
          </div>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset className="min-h-screen bg-background">
        <div className="flex min-h-12 items-center gap-3 border-b border-border bg-card px-4 md:hidden">
          <SidebarTrigger aria-label="Mở điều hướng" className="-ml-2" />
          <span className="text-sm font-semibold text-ink">Phân tích tài chính</span>
        </div>

        {context && <header className="border-b border-border bg-card">{context}</header>}

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
      <SidebarMenuButton asChild isActive={isCurrent} size="lg">
        <NavLink to={to} aria-current={isCurrent ? 'page' : undefined}>
          <Icon aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}
