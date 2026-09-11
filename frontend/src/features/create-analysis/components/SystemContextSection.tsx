import { ArrowRight, CheckCircle2, CircleAlert, CircleX, Workflow } from 'lucide-react';
import type { AnalysisCapabilities } from '../../../entities/capability/model/types';
import { cn } from '../../../shared/lib/cn';

interface SystemContextSectionProps {
  capabilities: AnalysisCapabilities;
}

const macroCopy = {
  AVAILABLE: { label: 'KHẢ DỤNG', icon: CheckCircle2, tone: 'text-ready' },
  LIMITED: { label: 'HẠN CHẾ', icon: CircleAlert, tone: 'text-warning' },
  UNAVAILABLE: { label: 'KHÔNG KHẢ DỤNG', icon: CircleX, tone: 'text-blocked' }
} as const;

export function SystemContextSection({ capabilities }: SystemContextSectionProps) {
  const copy = macroCopy[capabilities.macro.status];
  const StatusIcon = copy.icon;
  const steps = ['Bối cảnh vĩ mô', 'Đối sánh nhóm tham chiếu', 'Phân tích doanh nghiệp', 'Tổng hợp', 'Kiểm tra & hiệu chỉnh', 'Xuất báo cáo'];

  return (
    <section className="surface-section" aria-labelledby="system-context-heading">
      <div className="flex items-start gap-3">
        <Workflow size={18} className="mt-0.5 text-[#1c5d9c]" aria-hidden="true" />
        <div>
          <h2 id="system-context-heading" className="section-title">Bối cảnh hệ thống</h2>
          <p className="section-helper">Macro · Nhóm tham chiếu · Tổng hợp bằng chứng</p>
        </div>
      </div>

      <div className="mt-4 border border-line bg-[#fbfbf9] px-4 py-2.5">
        <div className="flex flex-wrap items-start gap-x-5 gap-y-2">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-ink">Macro</span>
            <StatusIcon size={17} className={copy.tone} aria-hidden="true" />
            <span className={cn('font-semibold', copy.tone)}>{copy.label}</span>
          </div>
          <span className="hidden h-5 w-px bg-line sm:block" aria-hidden="true" />
          <p className="max-w-2xl text-xs leading-5 text-muted">{capabilities.macro.summary}</p>
        </div>
      </div>

      <div className="mt-4">
        <p className="text-xs font-semibold text-ink">Quy trình tự động</p>
        <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-2 text-xs text-muted" aria-label="Quy trình tự động">
          {steps.map((step, index) => (
            <span key={step} className="inline-flex items-center gap-2">
              <span className={cn(index === 0 ? 'font-semibold text-ink' : '')}>{step}</span>
              {index < steps.length - 1 && <ArrowRight size={14} className="text-slate-300" aria-hidden="true" />}
            </span>
          ))}
        </div>
        <p className="mt-3 text-xs text-muted">Các bước thuộc hệ thống và không có tùy chọn bật/tắt riêng lẻ.</p>
      </div>
    </section>
  );
}
