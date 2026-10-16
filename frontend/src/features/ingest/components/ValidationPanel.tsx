import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Info,
  ChevronRight,
  ShieldCheck,
  Ban,
} from 'lucide-react';
import { scrubUserText } from '../lib/scrubText';
import type { Validation, ValidationCheck } from '../model/types';

interface ValidationPanelProps {
  validation: Validation;
  onHighlightRows: (rowIds: string[]) => void;
  highlightedRowIds?: string[];
}

export function ValidationPanel({
  validation,
  onHighlightRows,
  highlightedRowIds = [],
}: ValidationPanelProps) {
  const errors = validation.checks.filter((c) => c.severity === 'error');
  const warnings = validation.checks.filter((c) => c.severity === 'warning');
  const infos = validation.checks.filter((c) => c.severity === 'info');

  const isPass = validation.status === 'pass' && validation.ready_to_confirm;

  return (
    <div
      className={`rounded-md border p-4 space-y-4 shadow-tactile ${
        isPass
          ? 'border-ready/40 bg-ready-soft/20'
          : validation.status === 'warn'
          ? 'border-warning/40 bg-warning-soft/20'
          : 'border-blocked/40 bg-blocked-soft/20'
      }`}
      data-testid="validation-panel"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-line pb-2.5">
        <div className="flex items-center gap-2">
          {isPass ? (
            <ShieldCheck className="size-5 text-ready shrink-0" aria-hidden="true" />
          ) : (
            <ShieldAlert className="size-5 text-blocked shrink-0" aria-hidden="true" />
          )}
          <div>
            <h3 className="text-sm font-bold text-ink">Kết quả kiểm tra tự động</h3>
            <p className="text-xs text-ink-secondary">
              Đẳng thức kế toán, thang đo số liệu và tính nhất quán giữa hai kỳ.
            </p>
          </div>
        </div>

        <div>
          {isPass ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-ready-soft px-2.5 py-0.5 text-xs font-semibold text-text-success border border-ready/40">
              <CheckCircle2 className="size-3.5" />
              Đạt chuẩn xác nhận
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-blocked-soft px-2.5 py-0.5 text-xs font-semibold text-blocked border border-blocked/40">
              <Ban className="size-3.5" />
              Chưa đủ điều kiện xác nhận
            </span>
          )}
        </div>
      </div>

      {/* Blocking Reasons if not ready */}
      {validation.blocking_reasons_vi && validation.blocking_reasons_vi.length > 0 && (
        <div className="rounded-md border border-blocked/30 bg-card p-3 space-y-1.5 text-xs">
          <div className="font-semibold text-blocked flex items-center gap-1.5">
            <AlertTriangle className="size-3.5" />
            Lý do chưa thể nhập vào hệ thống:
          </div>
          <ul className="list-disc list-inside space-y-1 text-ink pl-1">
            {validation.blocking_reasons_vi.map((reason, idx) => (
              <li key={idx} className="leading-relaxed">
                {scrubUserText(reason)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Checks Group: Errors */}
      {errors.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-bold uppercase tracking-wider text-blocked flex items-center gap-1.5">
            <ShieldAlert className="size-3.5" />
            Lỗi chặn ({errors.length}):
          </div>
          <div className="space-y-1.5">
            {errors.map((check, idx) => (
              <CheckItem
                key={idx}
                check={check}
                onHighlight={onHighlightRows}
                isHighlighted={check.row_ids.some((id) => highlightedRowIds.includes(id))}
              />
            ))}
          </div>
        </div>
      )}

      {/* Checks Group: Warnings */}
      {warnings.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-bold uppercase tracking-wider text-text-warning flex items-center gap-1.5">
            <AlertTriangle className="size-3.5" />
            Cảnh báo ({warnings.length}):
          </div>
          <div className="space-y-1.5">
            {warnings.map((check, idx) => (
              <CheckItem
                key={idx}
                check={check}
                onHighlight={onHighlightRows}
                isHighlighted={check.row_ids.some((id) => highlightedRowIds.includes(id))}
              />
            ))}
          </div>
        </div>
      )}

      {/* Checks Group: Infos */}
      {infos.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-bold uppercase tracking-wider text-ink-secondary flex items-center gap-1.5">
            <Info className="size-3.5" />
            Thông tin kiểm tra ({infos.length}):
          </div>
          <div className="space-y-1.5">
            {infos.map((check, idx) => (
              <CheckItem
                key={idx}
                check={check}
                onHighlight={onHighlightRows}
                isHighlighted={check.row_ids.some((id) => highlightedRowIds.includes(id))}
              />
            ))}
          </div>
        </div>
      )}

      {/* When no checks found */}
      {validation.checks.length === 0 && isPass && (
        <div className="rounded border border-ready/30 bg-card p-3 text-xs text-text-success flex items-center gap-2">
          <CheckCircle2 className="size-4 shrink-0" />
          <span>Tất cả các phép thử kiểm tra tự động đều hợp lệ. Dữ liệu đã sẵn sàng để nhập.</span>
        </div>
      )}
    </div>
  );
}

function CheckItem({
  check,
  onHighlight,
  isHighlighted,
}: {
  check: ValidationCheck;
  onHighlight: (rowIds: string[]) => void;
  isHighlighted: boolean;
}) {
  const hasRows = check.row_ids && check.row_ids.length > 0;

  return (
    <div
      onClick={() => hasRows && onHighlight(check.row_ids)}
      className={`rounded border p-2.5 text-xs transition-colors cursor-pointer flex items-start justify-between gap-2 bg-card ${
        isHighlighted
          ? 'border-amber ring-1 ring-amber bg-amber-soft/20'
          : check.severity === 'error'
          ? 'border-blocked/30 hover:border-blocked/60'
          : 'border-warning/30 hover:border-warning/60'
      }`}
    >
      <div className="space-y-1 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={`font-semibold ${
              check.severity === 'error' ? 'text-blocked' : 'text-text-warning'
            }`}
          >
            {scrubUserText(check.message_vi)}
          </span>
        </div>

        {(check.expected || check.actual) && (
          <div className="font-mono text-[11px] text-ink-secondary flex items-center gap-3">
            {check.expected && <span>Kỳ vọng: {scrubUserText(check.expected)}</span>}
            {check.actual && <span>Thực tế: {scrubUserText(check.actual)}</span>}
          </div>
        )}
      </div>

      {hasRows && (
        <span className="text-[11px] text-text-accent font-medium shrink-0 flex items-center gap-0.5 hover:underline">
          <span>Xem dòng ({check.row_ids.length})</span>
          <ChevronRight className="size-3" />
        </span>
      )}
    </div>
  );
}
