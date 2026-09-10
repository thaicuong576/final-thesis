import { CheckCircle2, Clock3, Database, Info, X } from 'lucide-react';
import type { AnalysisCapabilities } from '../../../entities/capability/model/types';
import { cn } from '../../../shared/lib/cn';

interface CapabilityDetailsDrawerProps {
  capabilities: AnalysisCapabilities;
  open: boolean;
  onClose: () => void;
}

const macroLabel: Record<AnalysisCapabilities['macro']['status'], string> = {
  AVAILABLE: 'KHẢ DỤNG',
  LIMITED: 'HẠN CHẾ',
  UNAVAILABLE: 'KHÔNG KHẢ DỤNG'
};

export function CapabilityDetailsDrawer({ capabilities, open, onClose }: CapabilityDetailsDrawerProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="presentation">
      <button aria-label="Đóng chi tiết phạm vi dữ liệu" className="absolute inset-0 cursor-default bg-ink/20" onClick={onClose} />
      <aside
        aria-label="Chi tiết phạm vi dữ liệu"
        aria-modal="true"
        className="absolute right-0 top-0 flex h-full w-full max-w-[440px] flex-col overflow-y-auto border-l border-line bg-canvas shadow-2xl"
        role="dialog"
      >
        <div className="flex items-start justify-between border-b border-line bg-white px-6 py-5">
          <div>
            <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Năng lực hiện tại</p>
            <h2 className="font-display text-3xl font-semibold leading-none text-ink">Chi tiết phạm vi</h2>
          </div>
          <button type="button" aria-label="Đóng" onClick={onClose} className="rounded-sm p-2 text-muted transition hover:bg-selected hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1c5d9c]">
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <div className="space-y-6 px-6 py-6 text-sm">
          <DetailGroup title="Đối tượng được hỗ trợ">
            <div className="flex flex-wrap gap-2">
              {capabilities.entities.map((entity) => <span key={entity.id} className="border border-line bg-white px-2.5 py-1 font-semibold text-ink">{entity.ticker}</span>)}
            </div>
          </DetailGroup>

          <DetailGroup title="Chỉ tiêu">
            <ul className="space-y-2">
              {capabilities.metrics.map((metric) => <li key={metric.id} className="flex gap-2"><CheckCircle2 size={16} className="mt-0.5 text-ready" aria-hidden="true" /><span><strong>{metric.acronym}</strong> — {metric.label}</span></li>)}
            </ul>
          </DetailGroup>

          <DetailGroup title="Kỳ dữ liệu tài chính">
            <p className="font-semibold text-ink">{capabilities.financialDataPeriod}</p>
          </DetailGroup>

          <DetailGroup title="Nhóm tham chiếu">
            <p className="font-semibold text-ink">{capabilities.peerUniverse.label} · Chỉ đọc</p>
            <p className="mt-1 text-muted">{capabilities.peerUniverse.description}</p>
          </DetailGroup>

          <DetailGroup title="Macro Gold">
            <div className="flex items-start gap-2">
              <Info size={17} className={cn('mt-0.5', {
                'text-ready': capabilities.macro.status === 'AVAILABLE',
                'text-warning': capabilities.macro.status === 'LIMITED',
                'text-blocked': capabilities.macro.status === 'UNAVAILABLE'
              })} aria-hidden="true" />
              <div><p className="font-semibold text-ink">{macroLabel[capabilities.macro.status]}</p><p className="mt-1 text-muted">{capabilities.macro.details}</p></div>
            </div>
          </DetailGroup>

          <DetailGroup title="Phiên bản và thời gian">
            <dl className="space-y-3">
              <DetailRow icon={<Database size={15} />} label="Phiên bản dữ liệu" value={capabilities.goldVersion} />
              <DetailRow icon={<Clock3 size={15} />} label="Kỳ tài chính" value={capabilities.financialDataPeriod} />
              <DetailRow icon={<Clock3 size={15} />} label="Nạp/cập nhật dữ liệu" value={capabilities.ingestionTimestamp} />
              <DetailRow icon={<CheckCircle2 size={15} />} label="Xác thực dữ liệu" value={capabilities.validationTimestamp} />
            </dl>
          </DetailGroup>

          <DetailGroup title="Nguồn và readiness">
            <p className="text-muted">Nguồn: <span className="text-ink">{capabilities.source}</span></p>
            <p className="mt-2 text-muted">Trạng thái: <span className="text-ink">{capabilities.readiness}</span></p>
          </DetailGroup>
        </div>
      </aside>
    </div>
  );
}

function DetailGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="border-t border-line pt-4 first:border-t-0 first:pt-0"><h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.13em] text-muted">{title}</h3>{children}</section>;
}

function DetailRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="flex gap-2"><span className="mt-0.5 text-muted" aria-hidden="true">{icon}</span><div><dt className="text-xs text-muted">{label}</dt><dd className="mt-0.5 text-ink">{value}</dd></div></div>;
}
