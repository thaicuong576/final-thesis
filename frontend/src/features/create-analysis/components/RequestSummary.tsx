import { CheckCircle2, CircleAlert, CircleX, Play } from 'lucide-react';
import type { AnalysisCapabilities, MacroCapabilityStatus } from '../../../entities/capability/model/types';
import type { AnalysisFormValues } from '../schema';
import { cn } from '../../../shared/lib/cn';
import { formatPeriodLabel } from '../../../shared/lib/formatting';

interface RequestSummaryProps {
  capabilities: AnalysisCapabilities;
  values: AnalysisFormValues;
  isValid: boolean;
  isSubmitting: boolean;
  submissionMessage: string | null;
  onSubmit: () => void;
}

const macroLabel: Record<MacroCapabilityStatus, string> = {
  AVAILABLE: 'KHẢ DỤNG',
  LIMITED: 'HẠN CHẾ',
  UNAVAILABLE: 'KHÔNG KHẢ DỤNG'
};

export function RequestSummary({ capabilities, values, isValid, isSubmitting, submissionMessage, onSubmit }: RequestSummaryProps) {
  const targetLabels = capabilities.entities.filter((entity) => values.analysisTargetIds.includes(entity.id)).map((entity) => entity.ticker);
  const periodLabels = capabilities.periods.filter((period) => values.periodIds.includes(period.id)).map(formatPeriodLabel);
  const metricLabels = capabilities.metrics.filter((metric) => values.metricIds.includes(metric.id)).map((metric) => metric.acronym);
  const blockedByMacro = capabilities.macro.status === 'UNAVAILABLE';
  const ready = isValid && !blockedByMacro;
  const StatusIcon = blockedByMacro ? CircleX : ready ? CheckCircle2 : CircleAlert;
  const statusTone = blockedByMacro ? 'text-blocked' : ready ? 'text-ready' : 'text-warning';

  return (
    <aside className="sticky-summary" aria-label="Tóm tắt yêu cầu">
      <h2 className="font-display text-[28px] font-semibold leading-tight text-ink">Tóm tắt yêu cầu</h2>
      <div className="mt-5 divide-y divide-line border-y border-line">
        <SummaryRow label="Mục tiêu" value={values.objective || 'Chưa có'} multiline />
        <SummaryRow label="Đối tượng phân tích" value={targetLabels.length ? targetLabels.join(' · ') : 'Chưa chọn'} />
        <SummaryRow label="Kỳ tài chính" value={periodLabels.length ? periodLabels.join(' · ') : 'Chưa chọn'} />
        <SummaryRow label="Chỉ tiêu" value={metricLabels.length ? metricLabels.join(' · ') : 'Chưa chọn'} />
        <SummaryRow label="Nhóm tham chiếu" value={`${capabilities.peerUniverse.entityIds.length} ngân hàng · Chỉ đọc`} helper="Các ngân hàng không được chọn vẫn có thể xuất hiện trong báo cáo." />
        <SummaryRow label="Macro" value={macroLabel[capabilities.macro.status]} valueTone={statusTone} helper={capabilities.macro.status === 'LIMITED' ? 'Giới hạn sẽ được công bố trong báo cáo.' : undefined} />
      </div>

      <div className="mt-6">
        <p className="text-xs font-semibold uppercase tracking-[0.13em] text-muted">Trạng thái kiểm tra</p>
        <div className="mt-3 flex items-start gap-2">
          <StatusIcon size={19} className={statusTone} aria-hidden="true" />
          <div>
            <p className={cn('text-sm font-semibold', statusTone)}>{blockedByMacro ? 'Chưa thể chạy' : ready ? 'Sẵn sàng để chạy' : 'Chưa đủ thông tin'}</p>
            <p className="mt-1 text-xs leading-5 text-muted">{blockedByMacro ? 'Hợp đồng Macro tối thiểu chưa đáp ứng.' : ready ? `Macro: ${macroLabel[capabilities.macro.status]} · phạm vi đã được kiểm tra phía giao diện.` : 'Hoàn thiện mục tiêu và phạm vi để tiếp tục.'}</p>
          </div>
        </div>
      </div>

      <button type="button" disabled={!ready || isSubmitting} onClick={onSubmit} className="primary-button mt-6 w-full">
        <Play size={16} fill="currentColor" aria-hidden="true" />
        {isSubmitting ? 'Đang kiểm tra…' : 'Chạy phân tích'}
      </button>
      {submissionMessage && <p className="mt-3 border border-[#b8d7ca] bg-[#f1f8f4] px-3 py-2 text-xs leading-5 text-ready" role="status">{submissionMessage}</p>}
    </aside>
  );
}

function SummaryRow({ label, value, helper, multiline, valueTone }: { label: string; value: string; helper?: string; multiline?: boolean; valueTone?: string }) {
  return (
    <div className="grid gap-1 py-3 sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.35fr)] sm:gap-4">
      <dt className="text-xs font-semibold text-muted">{label}</dt>
      <dd className={cn('text-sm text-ink', multiline ? 'line-clamp-3 leading-5' : '', valueTone)}>
        <span>{value}</span>
        {helper && <span className="mt-1 block text-xs leading-5 text-muted">{helper}</span>}
      </dd>
    </div>
  );
}
