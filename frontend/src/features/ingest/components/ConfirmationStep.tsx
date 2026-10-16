import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  Database,
  ArrowRight,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { normalizeLimitations } from '@/features/onboarding/normalizeLimitations';
import { formatPeriodCode } from '@/shared/lib/formatting';
import type { ConfirmResult } from '../model/types';

interface ConfirmationStepProps {
  readyToConfirm: boolean;
  isConfirming: boolean;
  onConfirm: () => Promise<void>;
  confirmResult: ConfirmResult | null;
  entityId: string;
}

const METRIC_LABELS: Record<string, { label: string; unit: string }> = {
  'bank.npl_g35': { label: 'Tỷ lệ nợ xấu (NPL nhóm 3–5)', unit: '%' },
  'npl_g35': { label: 'Tỷ lệ nợ xấu (NPL nhóm 3–5)', unit: '%' },
  'bank.llr_coverage': { label: 'Tỷ lệ bao phủ nợ xấu (LLR)', unit: '%' },
  'llr_coverage': { label: 'Tỷ lệ bao phủ nợ xấu (LLR)', unit: '%' },
  'bank.roa': { label: 'Tỷ suất sinh lời trên tài sản (ROA)', unit: '%' },
  'roa': { label: 'Tỷ suất sinh lời trên tài sản (ROA)', unit: '%' },
  'bank.roe': { label: 'Tỷ suất sinh lời trên vốn CSH (ROE)', unit: '%' },
  'roe': { label: 'Tỷ suất sinh lời trên vốn CSH (ROE)', unit: '%' },
};

function formatMetricValue(val: number | null | undefined, unit: string): string {
  if (val === null || val === undefined) return '—';
  return `${val.toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${unit}`;
}

export function ConfirmationStep({
  readyToConfirm,
  isConfirming,
  onConfirm,
  confirmResult,
  entityId,
}: ConfirmationStepProps) {
  const navigate = useNavigate();

  const handleAsk = () => {
    if (!confirmResult) return;
    const bank = confirmResult.entity_id;
    const params = new URLSearchParams({
      upload_id: confirmResult.upload_id,
      entity: bank,
      period: confirmResult.period_id,
      q: `Tỷ lệ nợ xấu của ${bank} là bao nhiêu?`,
    });
    navigate(`/analysis?${params.toString()}`);
  };

  // If already confirmed: light, quiet presentation of the 4 recomputed metrics
  if (confirmResult) {
    const limitations = normalizeLimitations(confirmResult.limitations_vi);

    return (
      <div
        className="rounded-md border border-line bg-card p-5 space-y-4"
        data-testid="confirmation-result-card"
        data-upload-id={confirmResult.upload_id}
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-line pb-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-5 text-ready shrink-0" aria-hidden="true" />
            <h3 className="text-sm font-bold text-ink">
              Đã nhập thành công vào cơ sở dữ liệu: {confirmResult.entity_id} ({formatPeriodCode(confirmResult.period_id)})
            </h3>
          </div>

          <Button
            type="button"
            onClick={handleAsk}
            className="h-8 border border-amber-border bg-amber px-4 text-xs font-semibold text-ink shadow-sm hover:bg-amber-hover transition shrink-0"
            data-testid="ask-about-bank-button"
          >
            <span>Hỏi về {confirmResult.entity_id}</span>
            <ArrowRight className="ml-1.5 size-3.5" />
          </Button>
        </div>

        {/* 4 Recomputed Core Metrics */}
        {confirmResult.metrics && confirmResult.metrics.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-ink-secondary">
              Kết quả 4 chỉ tiêu tài chính tính lại từ đầu vào đã duyệt:
            </div>

            {/* Desktop Table View */}
            <div className="hidden sm:block overflow-x-auto rounded border border-line bg-card">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-line bg-surface-secondary/60 text-ink-secondary">
                    <th className="py-2 px-3 font-semibold">Chỉ tiêu cốt lõi</th>
                    <th className="py-2 px-3 text-right font-semibold">Giá trị tính lại</th>
                    <th className="py-2 px-3 text-right font-semibold">Giá trị công bố</th>
                    <th className="py-2 px-3 text-center font-semibold">Trạng thái</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {confirmResult.metrics.map((m) => {
                    const info =
                      METRIC_LABELS[m.metric_id] ||
                      METRIC_LABELS[m.metric_id.replace('bank.', '')] || {
                        label: 'Chỉ tiêu tài chính',
                        unit: '%',
                      };
                    const isMatch =
                      m.status === 'valid' || m.status === 'matched' || m.status === 'computed';
                    return (
                      <tr key={m.metric_id} className="hover:bg-surface-secondary/30 transition-colors">
                        <td className="py-2 px-3">
                          <span className="font-semibold text-ink">{info.label}</span>
                        </td>
                        <td className="py-2 px-3 text-right font-mono font-bold text-ink tabular-nums">
                          {formatMetricValue(m.computed_value, info.unit)}
                        </td>
                        <td className="py-2 px-3 text-right font-mono text-ink-secondary tabular-nums">
                          {formatMetricValue(m.reported_value, info.unit)}
                        </td>
                        <td className="py-2 px-3 text-center">
                          <span
                            className={`text-[11px] font-medium ${
                              isMatch ? 'text-text-success' : 'text-blocked'
                            }`}
                          >
                            {isMatch ? 'Khớp' : 'Lệch dung sai'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Stacked Items (<= 640px) */}
            <div className="sm:hidden divide-y divide-line rounded border border-line bg-card" data-testid="confirmed-metrics-mobile">
              {confirmResult.metrics.map((m) => {
                const info =
                  METRIC_LABELS[m.metric_id] ||
                  METRIC_LABELS[m.metric_id.replace('bank.', '')] || {
                    label: 'Chỉ tiêu tài chính',
                    unit: '%',
                  };
                const isMatch =
                  m.status === 'valid' || m.status === 'matched' || m.status === 'computed';
                return (
                  <div key={m.metric_id} className="p-2.5 text-xs space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-ink">{info.label}</span>
                      <span
                        className={`text-[10px] font-medium ${
                          isMatch ? 'text-text-success' : 'text-blocked'
                        }`}
                      >
                        {isMatch ? 'Khớp' : 'Lệch dung sai'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-ink-secondary">Giá trị tính lại:</span>
                      <span className="font-mono font-bold text-ink tabular-nums">
                        {formatMetricValue(m.computed_value, info.unit)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-ink-secondary">Giá trị công bố:</span>
                      <span className="font-mono text-ink-secondary tabular-nums">
                        {formatMetricValue(m.reported_value, info.unit)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Limitations Notice */}
        {limitations.length > 0 && (
          <div className="text-xs text-ink-secondary pt-1 border-t border-line space-y-0.5">
            <span className="font-semibold text-ink">Ghi chú phạm vi: </span>
            {limitations.map((lim, idx) => (
              <span key={idx}>{lim} </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Ready to confirm button
  return (
    <div
      className="rounded-md border border-line bg-card p-4 space-y-2.5"
      data-testid="ready-to-confirm-box"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h3 className="text-xs font-bold text-ink flex items-center gap-1.5">
            <Database className="size-3.5 text-text-accent" />
            Nhập số liệu vào cơ sở dữ liệu phân tích
          </h3>
          <p className="text-[11px] text-ink-secondary mt-0.5">
            Tạo bản chụp vận hành độc lập cho {entityId}. Sẵn sàng để hỏi đáp và so sánh.
          </p>
        </div>

        <Button
          type="button"
          disabled={!readyToConfirm || isConfirming}
          onClick={onConfirm}
          className="h-8 border border-amber-border bg-amber px-4 text-xs font-semibold text-ink shadow-sm hover:bg-amber-hover transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          data-testid="confirm-filing-button"
        >
          {isConfirming ? (
            <>
              <Loader2 className="mr-1.5 size-3.5 animate-spin" />
              Đang tạo snapshot vận hành…
            </>
          ) : (
            <>
              <span>Nhập vào cơ sở dữ liệu</span>
              <ArrowRight className="ml-1.5 size-3.5" />
            </>
          )}
        </Button>
      </div>

      {!readyToConfirm && (
        <div className="text-[11px] text-ink-tertiary flex items-center gap-1.5">
          <AlertTriangle className="size-3 text-warning shrink-0" />
          <span>
            Nút nhập sẽ bật khi tất cả các dòng cần dùng đã được xác nhận và không còn lỗi chặn kiểm tra.
          </span>
        </div>
      )}
    </div>
  );
}
