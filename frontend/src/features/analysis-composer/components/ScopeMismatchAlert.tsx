import type { ScopeMismatch } from '../model/types';
import { Button } from '@/components/ui/button';
import { AlertCircle, RefreshCw, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

interface ScopeMismatchAlertProps {
  mismatch: ScopeMismatch;
  rawQuestion: string;
  onEditQuestion: () => void;
}

export function ScopeMismatchAlert({
  mismatch,
  rawQuestion,
  onEditQuestion
}: ScopeMismatchAlertProps) {
  return (
    <div className="border border-warning/40 bg-card rounded-md p-5 space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-md bg-warning-soft border border-warning/30 text-warning flex items-center justify-center shrink-0">
          <AlertCircle className="w-4 h-4 stroke-[2.2]" />
        </div>
        <div className="space-y-1 min-w-0">
          <h2 className="text-sm font-bold text-ink">
            Phạm vi yêu cầu chưa được hỗ trợ trong bộ dữ liệu này
          </h2>
          <p className="text-xs text-ink-secondary italic truncate">
            “{rawQuestion}”
          </p>
        </div>
      </div>

      <div className="p-3.5 bg-warning-soft/60 border border-warning/30 rounded-md text-xs space-y-2 text-[#6e5225]">
        <p className="font-semibold text-xs text-[#6e5225]">
          {mismatch.reason || 'Yêu cầu phân tích vượt quá phạm vi dữ liệu đã kiểm định.'}
        </p>

        <div className="text-[11px] font-mono space-y-1 text-ink-secondary border-t border-warning/20 pt-2">
          <p className="font-bold text-ink uppercase tracking-wider text-[10px]">Phạm vi sẵn sàng trong bộ dữ liệu hiện hành:</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pl-1">
            <div>• Chu kỳ hỗ trợ: <strong className="text-ink">{mismatch.availableCapabilitiesSummary.periods}</strong></div>
            <div>• Ngân hàng hỗ trợ: <strong className="text-ink">{mismatch.availableCapabilitiesSummary.entities}</strong></div>
            <div className="sm:col-span-2">• Chỉ tiêu hỗ trợ: <strong className="text-ink">{mismatch.availableCapabilitiesSummary.metrics}</strong></div>
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-line">
        <Button
          type="button"
          variant="outline"
          onClick={onEditQuestion}
          className="text-xs font-semibold gap-1.5 self-start sm:self-auto"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Chỉnh câu hỏi</span>
        </Button>

        <Button asChild className="h-9 px-4 text-xs font-semibold gap-1.5 self-end sm:self-auto">
          <Link to="/data"><RefreshCw className="w-3.5 h-3.5" aria-hidden="true" /><span>Xem phạm vi dữ liệu</span></Link>
        </Button>
      </div>
    </div>
  );
}
