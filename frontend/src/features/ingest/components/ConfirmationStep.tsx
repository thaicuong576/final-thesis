import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  Database,
  ArrowRight,
  Loader2,
  FileText,
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

  // If already confirmed
  if (confirmResult) {
    const isAccepted = confirmResult.status === 'accepted';
    const limitations = normalizeLimitations(confirmResult.limitations_vi);

    return (
      <div
        className={`rounded-md border p-5 space-y-4 shadow-tactile ${
          isAccepted ? 'border-ready/40 bg-ready-soft/20' : 'border-blocked/40 bg-blocked-soft/20'
        }`}
        data-testid="confirmation-result-card"
        data-upload-id={confirmResult.upload_id}
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-line pb-3">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="size-6 text-ready shrink-0" aria-hidden="true" />
            <div>
              <h3 className="text-sm font-bold text-ink">
                Đã nhập thành công vào cơ sở dữ liệu: {confirmResult.entity_id} ({formatPeriodCode(confirmResult.period_id)})
              </h3>
            </div>
          </div>

          <Button
            type="button"
            onClick={handleAsk}
            className="h-9 border border-amber-border bg-amber px-4 text-xs font-semibold text-ink shadow-tactile hover:bg-amber-hover transition shrink-0"
            data-testid="ask-about-bank-button"
          >
            <span>Hỏi về {confirmResult.entity_id}</span>
            <ArrowRight className="ml-1.5 size-3.5" />
          </Button>
        </div>

        {/* 4 Recomputed Core Metrics */}
        {confirmResult.metrics && confirmResult.metrics.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-bold uppercase tracking-wide text-ink-secondary">
              Kết quả 4 chỉ tiêu tài chính tính lại từ đầu vào đã duyệt:
            </div>

            {/* Desktop Table View (>= 640px) */}
            <div className="hidden sm:block overflow-x-auto rounded border border-line bg-card shadow-sm">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-line bg-surface-secondary text-ink-secondary">
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
                      <tr key={m.metric_id} className="hover:bg-surface-hover/30 transition-colors">
                        <td className="py-2 px-3">
                          <span className="font-semibold text-ink">{info.label}</span>
                        </td>
                        <td className="py-2 px-3 text-right font-mono font-bold text-ink">
                          {formatMetricValue(m.computed_value, info.unit)}
                        </td>
                        <td className="py-2 px-3 text-right font-mono text-ink-secondary">
                          {formatMetricValue(m.reported_value, info.unit)}
                        </td>
                        <td className="py-2 px-3 text-center">
                          {isMatch ? (
                            <span className="inline-flex items-center rounded-full bg-ready-soft px-2 py-0.5 text-[11px] font-medium text-text-success border border-ready/30">
                              Hợp lệ
                            </span>
                          ) : (
                            <span className="inline-flex items-center rounded-full bg-blocked-soft px-2 py-0.5 text-[11px] font-medium text-blocked border border-blocked/30">
                              Lệch dung sai
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Stacked Items (<= 640px) */}
            <div className="sm:hidden space-y-2" data-testid="confirmed-metrics-mobile">
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
                  <div
                    key={m.metric_id}
                    className="rounded border border-line bg-card p-2.5 text-xs shadow-sm space-y-1.5"
                  >
                    <div className="flex items-center justify-between gap-2 border-b border-line pb-1">
                      <span className="font-bold text-ink">{info.label}</span>
                      {isMatch ? (
                        <span className="inline-flex items-center rounded-full bg-ready-soft px-2 py-0.5 text-[10px] font-medium text-text-success border border-ready/30">
                          Hợp lệ
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-blocked-soft px-2 py-0.5 text-[10px] font-medium text-blocked border border-blocked/30">
                          Lệch dung sai
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-ink-secondary">Giá trị tính lại:</span>
                      <span className="font-mono font-bold text-ink">
                        {formatMetricValue(m.computed_value, info.unit)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-ink-secondary">Giá trị công bố:</span>
                      <span className="font-mono text-ink-secondary">
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
          <div className="rounded-md border border-warning/40 bg-warning-soft/40 p-3 text-xs text-ink space-y-1">
            <div className="font-semibold text-text-warning flex items-center gap-1.5">
              <FileText className="size-3.5 text-warning" />
              Giới hạn sử dụng dữ liệu nạp mới:
            </div>
            {limitations.map((lim, idx) => (
              <p key={idx} className="leading-relaxed text-ink-secondary">
                {lim}
              </p>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Ready to confirm button
  return (
    <div
      className="rounded-md border border-line bg-card p-5 space-y-3 shadow-tactile"
      data-testid="ready-to-confirm-box"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-ink flex items-center gap-2">
            <Database className="size-4 text-text-accent" />
            Nhập số liệu vào cơ sở dữ liệu phân tích
          </h3>
          <p className="text-xs text-ink-secondary mt-0.5">
            Tạo một bản chụp vận hành độc lập cho {entityId}. Dữ liệu sau khi nhập sẽ sẵn sàng để hỏi đáp và so sánh.
          </p>
        </div>

        <Button
          type="button"
          disabled={!readyToConfirm || isConfirming}
          onClick={onConfirm}
          className="h-9 border border-amber-border bg-amber px-4 text-xs font-semibold text-ink shadow-tactile hover:bg-amber-hover transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
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
