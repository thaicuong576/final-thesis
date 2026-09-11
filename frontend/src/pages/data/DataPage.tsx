import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { AddDataSourceDrawer } from '../../features/data/components/AddDataSourceDrawer';
import { useAnalysisDataset } from '../../features/data/hooks/useAnalysisDataset';
import type { DataSourceSummary } from '../../entities/dataset/model/types';
import { cn } from '../../shared/lib/cn';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
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
} from '../../components/ui/sidebar';
import { Separator } from '../../components/ui/separator';
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  CircleAlert,
  Database,
  FileText,
  Plus,
  UserRound,
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';

export function DataPage() {
  const datasetQuery = useAnalysisDataset();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  const showNotice = useCallback((message: string) => setNotice(message), []);

  useEffect(() => {
    const previousTitle = document.title;
    document.title = 'Dữ liệu phân tích · Phân tích tài chính';

    return () => {
      document.title = previousTitle;
    };
  }, []);

  if (datasetQuery.isPending) return <LoadingState />;
  if (datasetQuery.isError || !datasetQuery.data) return <ErrorState />;

  const { summary, sources } = datasetQuery.data;
  const structuredSource = sources.find((source) => source.kind === 'structured');
  const documentSource = sources.find((source) => source.kind === 'documents');

  return (
    <SidebarProvider defaultOpen className="bg-canvas text-ink">
      <Sidebar collapsible="none" className="border-sidebar-border bg-sidebar">
        <SidebarHeader className="p-6 pb-5">
          <Link to="/data" className="flex items-center gap-2.5 text-sm font-semibold tracking-[-0.01em] text-ink">
            <span className="grid size-7 place-items-center bg-[#1c5d9c] text-white" aria-hidden="true">
              <BarChart3 size={16} strokeWidth={2.5} />
            </span>
            <span>Financial Analysis</span>
          </Link>
        </SidebarHeader>

        <SidebarSeparator className="mx-0 w-full" />

        <SidebarContent>
          <SidebarGroup className="p-4 pt-5">
            <SidebarMenu>
              <NavItem to="/data" label="Dữ liệu" />
              <NavItem to="/analysis/new" label="Tạo phân tích" />
              <SidebarMenuItem>
                <SidebarMenuButton disabled className="text-slate-400">
                  Báo cáo
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter className="p-0">
          <SidebarSeparator className="mx-0 w-full" />
          <div className="p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Tài khoản</p>
            <div className="mt-3 flex items-center gap-2.5 text-xs font-semibold text-ink">
              <span className="grid size-8 place-items-center rounded-full bg-[#273a50] text-[10px] text-white">PTC</span>
              <span>Phùng Thái Cường</span>
              <UserRound size={15} className="ml-auto text-muted" aria-hidden="true" />
            </div>
          </div>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset className="min-h-screen bg-canvas">
        <div className="border-b border-line bg-white px-5 py-3 md:hidden">
          <SidebarTrigger aria-label="Mở điều hướng" className="-ml-2" />
        </div>

        <main className="min-w-0 flex-1">
          <div className="mx-auto max-w-[1180px] px-5 pb-16 pt-8 sm:px-8 lg:px-10 lg:pt-10">
            <header className="flex flex-col gap-5 border-b border-line pb-7 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h1 className="text-[2.15rem] font-semibold leading-none tracking-[-0.03em] text-ink">Dữ liệu phân tích</h1>
                <p className="mt-3 text-sm text-muted">Quản lý dữ liệu được sử dụng trong các báo cáo tài chính.</p>
              </div>
              <Button
                type="button"
                onClick={() => { setNotice(null); setDrawerOpen(true); }}
                className="h-11 rounded-sm bg-ink px-4 text-sm font-semibold text-white shadow-none hover:bg-[#263849]"
              >
                <Plus data-icon="inline-start" aria-hidden="true" />
                Thêm nguồn dữ liệu
              </Button>
            </header>

            <section className="mt-7 border border-line bg-white shadow-surface" aria-labelledby="active-dataset-heading">
              <div className="flex flex-col gap-4 px-5 py-5 sm:flex-row sm:items-start sm:justify-between sm:px-6">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <h2 id="active-dataset-heading" className="text-lg font-semibold tracking-[-0.015em] text-ink">Bộ dữ liệu đang sử dụng</h2>
                    <StatusBadge icon={<CheckCircle2 size={14} />} tone="ready" label="Sẵn sàng" />
                  </div>
                  <p className="mt-2 text-[1.55rem] font-semibold tracking-[-0.025em] text-ink">{summary.name}</p>
                  <p className="mt-1 max-w-[62ch] text-sm leading-6 text-muted">Bộ dữ liệu đã được xác thực và có thể sử dụng trong hệ thống phân tích.</p>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted"><Database size={15} aria-hidden="true" /> Cập nhật 11/09/2026</div>
              </div>

              <dl className="grid border-y border-line sm:grid-cols-4">
                <DatasetFact label="Doanh nghiệp" value={`${summary.entityCount}`} suffix="doanh nghiệp" />
                <DatasetFact label="Kỳ dữ liệu" value={summary.periodLabel} />
                <DatasetFact label="Chỉ tiêu" value={`${summary.metricCount}`} suffix="chỉ tiêu" />
                <DatasetFact label="Tài liệu nguồn" value={`${summary.documentCount}`} suffix="tài liệu" />
              </dl>

              <div className="grid gap-6 px-5 py-5 sm:px-6 lg:grid-cols-[1fr_auto] lg:items-end">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Phạm vi hỗ trợ</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-3">
                    <ScopeStatus icon={<CheckCircle2 size={15} />} label="Doanh nghiệp" detail={summary.scope.entities} tone="ready" />
                    <ScopeStatus icon={<CheckCircle2 size={15} />} label="Nhóm tham chiếu" detail={summary.scope.peerUniverse} tone="ready" />
                    <ScopeStatus icon={<CircleAlert size={15} />} label="Vĩ mô" detail="Dữ liệu hạn chế" tone="warning" />
                  </div>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row lg:justify-end">
                  <Button type="button" variant="outline" onClick={() => showNotice('Bộ dữ liệu hiện tại đã được xác thực; chi tiết quan sát sẽ được mở trong phiên bản tiếp theo.')} className="h-10 rounded-sm border-line px-3 text-xs font-semibold shadow-none">Xem dữ liệu</Button>
                  <Button asChild className="h-10 rounded-sm bg-ink px-3 text-xs font-semibold shadow-none hover:bg-[#263849]"><Link to="/analysis/new">Dùng để phân tích <ArrowRight data-icon="inline-end" aria-hidden="true" /></Link></Button>
                </div>
              </div>
            </section>

            {notice && (
              <Alert className="mt-4 rounded-sm border-[#d7e5ef] bg-[#f5f8fb] py-3 text-[#41637e]" role="status">
                <AlertDescription className="text-sm">{notice}</AlertDescription>
              </Alert>
            )}

            <Separator className="my-10 bg-line" />

            <section aria-labelledby="sources-heading">
              <div className="flex items-end justify-between gap-4">
                <h2 id="sources-heading" className="text-[13px] font-semibold uppercase tracking-[0.14em] text-muted">Nguồn dữ liệu</h2>
                <span className="text-xs text-muted">Đóng góp vào bộ dữ liệu đang sử dụng</span>
              </div>
              <div className="mt-3 overflow-hidden border-y border-line bg-white">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="h-10 px-5 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted sm:px-6">Nguồn</TableHead>
                      <TableHead className="h-10 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">Kiểm tra</TableHead>
                      <TableHead className="h-10 pr-5 text-right text-[11px] font-semibold uppercase tracking-[0.1em] text-muted sm:pr-6">Thao tác</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {structuredSource && <SourceRow source={structuredSource} icon={<Database size={19} />} onDetails={() => showNotice('Dữ liệu tài chính ngân hàng: 80 quan sát, trong đó 4 giá trị thiếu cần được công bố khi phân tích.')} />}
                    {documentSource && <SourceRow source={documentSource} icon={<FileText size={19} />} onDetails={() => showNotice('Báo cáo và tài liệu nguồn: 17 tài liệu đã được lập chỉ mục để hỗ trợ đối chiếu bằng chứng.')} />}
                  </TableBody>
                </Table>
              </div>
            </section>
          </div>
        </main>
      </SidebarInset>

      <AddDataSourceDrawer
        key={drawerOpen ? 'open' : 'closed'}
        open={drawerOpen}
        onClose={closeDrawer}
        onCreated={(name) => showNotice(`Đã tạo bộ dữ liệu “${name}”. Bộ dữ liệu sẽ xuất hiện sau khi hệ thống hoàn tất xác thực.`)}
      />
    </SidebarProvider>
  );
}

function NavItem({ to, label }: { to: string; label: string }) {
  const location = useLocation();

  return (
    <SidebarMenuItem>
      <SidebarMenuButton asChild isActive={location.pathname === to}>
        <NavLink to={to}>{label}</NavLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}

function DatasetFact({ label, value, suffix }: { label: string; value: string; suffix?: string }) {
  return <div className="border-b border-line px-5 py-4 last:border-b-0 sm:border-b-0 sm:border-r sm:px-6 sm:last:border-r-0"><dt className="text-xs font-semibold text-muted">{label}</dt><dd className="mt-2 text-base font-semibold tabular-nums text-ink">{value} {suffix && <span className="text-xs font-medium text-muted">{suffix}</span>}</dd></div>;
}

function ScopeStatus({ icon, label, detail, tone }: { icon: ReactNode; label: string; detail: string; tone: 'ready' | 'warning' }) {
  return <div className="flex items-start gap-2 text-sm"><span className={tone === 'ready' ? 'text-ready' : 'text-warning'} aria-hidden="true">{icon}</span><span><span className="block font-semibold text-ink">{label}</span><span className="mt-0.5 block text-xs text-muted">{detail}</span></span></div>;
}

function StatusBadge({ icon, tone, label }: { icon: ReactNode; tone: 'ready' | 'warning'; label: string }) {
  return <Badge variant="outline" className={cn('h-6 gap-1.5 rounded-sm px-2 text-xs font-semibold', tone === 'ready' ? 'border-[#b8d7ca] bg-[#f1f8f4] text-ready' : 'border-[#ead6b5] bg-[#fffaf1] text-warning')}><span aria-hidden="true">{icon}</span>{label}</Badge>;
}

function SourceRow({ source, icon, onDetails }: { source: DataSourceSummary; icon: ReactNode; onDetails: () => void }) {
  const structured = source.kind === 'structured';
  return (
    <TableRow className="align-top hover:bg-[#fbfcfd]">
      <TableCell className="min-w-[250px] px-5 py-5 sm:px-6">
        <div className="flex items-start gap-3">
          <span className="grid size-9 shrink-0 place-items-center border border-line bg-[#fbfbf9] text-muted" aria-hidden="true">{icon}</span>
          <div>
            <div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold text-ink">{source.title}</h3><span className="text-xs text-muted">{source.typeLabel}</span></div>
            <div className="mt-2 flex flex-wrap items-center gap-2"><StatusBadge icon={<CheckCircle2 size={13} />} tone="ready" label={source.statusLabel} /><span className="text-xs text-muted">Cập nhật {source.updatedAt}</span></div>
          </div>
        </div>
      </TableCell>
      <TableCell className="min-w-[270px] py-5 text-sm text-muted">
        {structured ? <div className="flex flex-wrap gap-x-4 gap-y-1"><span><strong className="text-ink">{source.observationCount}</strong> quan sát</span><span><strong className="text-ink">{source.validObservationCount}</strong> hợp lệ</span><span className="text-warning"><strong>{source.missingValueCount}</strong> giá trị thiếu</span><span><strong className="text-ink">{source.duplicateCount}</strong> trùng</span></div> : <div><p><strong className="text-ink">{source.documentCount}</strong> tài liệu</p><p className="mt-1 text-xs leading-5">{source.examples?.join(' · ')}</p></div>}
      </TableCell>
      <TableCell className="whitespace-nowrap pr-5 text-right sm:pr-6"><Button type="button" variant="outline" size="sm" onClick={onDetails} className="rounded-sm border-line text-xs font-semibold shadow-none">Xem chi tiết</Button></TableCell>
    </TableRow>
  );
}

function LoadingState() {
  return <main className="grid min-h-screen place-items-center bg-canvas p-6"><div className="w-full max-w-md space-y-3" role="status" aria-label="Đang tải dữ liệu phân tích"><div className="h-7 w-2/3 animate-pulse bg-slate-200" /><div className="h-24 animate-pulse bg-white" /><div className="h-24 animate-pulse bg-white" /></div></main>;
}

function ErrorState() {
  return <main className="grid min-h-screen place-items-center bg-canvas p-6"><Alert className="max-w-md rounded-sm border-[#e4c0bb] bg-white"><AlertDescription><p className="font-semibold text-blocked">Không thể tải dữ liệu phân tích.</p><p className="mt-2 text-sm text-muted">Vui lòng thử lại khi dịch vụ dữ liệu sẵn sàng.</p></AlertDescription></Alert></main>;
}
