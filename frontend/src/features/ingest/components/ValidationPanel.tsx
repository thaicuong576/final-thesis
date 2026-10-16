import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { scrubUserText } from '../lib/scrubText';
import type { Validation } from '../model/types';

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

  const isPass = validation.status === 'pass' && validation.ready_to_confirm;

  return (
    <div
      className="rounded-md border border-line bg-card p-4 space-y-3"
      data-testid="validation-panel"
    >
      {/* 1-Sentence Summary */}
      <div className="flex items-center justify-between gap-2 border-b border-line pb-2">
        <div className="flex items-center gap-2">
          {isPass ? (
            <CheckCircle2 className="size-4 text-ready shrink-0" aria-hidden="true" />
          ) : (
            <ShieldAlert className="size-4 text-blocked shrink-0" aria-hidden="true" />
          )}
          <span className="text-xs text-ink">
            <span className="font-bold">
              {isPass ? 'Đạt chuẩn xác nhận' : 'Chưa đủ điều kiện xác nhận'}
            </span>
            <span className="text-ink-secondary">
              {isPass
                ? ': các phép thử kiểm tra tự động đều hợp lệ.'
                : ': cần giải quyết các điểm bên dưới.'}
            </span>
          </span>
        </div>
      </div>

      {/* Blocking Reasons & Errors First (Red text, no red boxes) */}
      {((validation.blocking_reasons_vi && validation.blocking_reasons_vi.length > 0) || errors.length > 0) && (
        <div className="space-y-1.5 text-xs">
          <div className="font-semibold text-blocked flex items-center gap-1.5">
            <AlertTriangle className="size-3.5 shrink-0" />
            <span>Lý do chưa thể nhập vào hệ thống:</span>
          </div>

          <ul className="space-y-1 pl-5 list-disc text-blocked text-xs">
            {validation.blocking_reasons_vi?.map((reason, idx) => (
              <li key={`reason-${idx}`} className="leading-relaxed">
                {scrubUserText(reason)}
              </li>
            ))}
            {errors.map((check, idx) => {
              const isActive = check.row_ids?.some((id) => highlightedRowIds.includes(id));
              return (
                <li key={`err-${idx}`} className="leading-relaxed">
                  <span>{scrubUserText(check.message_vi)}</span>
                  {check.row_ids && check.row_ids.length > 0 && (
                    <button
                      type="button"
                      onClick={() => onHighlightRows(check.row_ids!)}
                      className={`ml-1.5 inline-flex items-center text-[10px] cursor-pointer ${
                        isActive ? 'text-ink font-bold' : 'text-text-accent hover:underline'
                      }`}
                    >
                      <span>xem dòng ({check.row_ids.length})</span>
                      <ChevronRight className="size-2.5" />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Warnings Second */}
      {warnings.length > 0 && (
        <div className="space-y-1.5 text-xs pt-1">
          <div className="font-semibold text-warning flex items-center gap-1.5">
            <AlertTriangle className="size-3.5 shrink-0" />
            <span>Cảnh báo ({warnings.length}):</span>
          </div>
          <ul className="space-y-1 pl-5 list-disc text-ink-secondary text-xs">
            {warnings.map((check, idx) => {
              const isActive = check.row_ids?.some((id) => highlightedRowIds.includes(id));
              return (
                <li key={`warn-${idx}`} className="leading-relaxed">
                  <span>{scrubUserText(check.message_vi)}</span>
                  {check.row_ids && check.row_ids.length > 0 && (
                    <button
                      type="button"
                      onClick={() => onHighlightRows(check.row_ids!)}
                      className={`ml-1.5 inline-flex items-center text-[10px] cursor-pointer ${
                        isActive ? 'text-ink font-bold' : 'text-text-accent hover:underline'
                      }`}
                    >
                      <span>xem dòng ({check.row_ids.length})</span>
                      <ChevronRight className="size-2.5" />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Clean Success State */}
      {isPass && (
        <div className="text-xs text-text-success flex items-center gap-2 pt-0.5">
          <span>Số liệu cân đối kế toán và nhất quán giữa hai kỳ. Sẵn sàng nhập vào cơ sở dữ liệu.</span>
        </div>
      )}
    </div>
  );
}
