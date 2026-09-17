import type { ScopeMismatch } from '../model/types';
import { Button } from '@/components/ui/button';
import { AlertCircle, RefreshCw, ArrowLeft } from 'lucide-react';

interface ScopeMismatchAlertProps {
  mismatch: ScopeMismatch;
  rawQuestion: string;
  onEditQuestion: () => void;
  onOpenDatasetSelector: () => void;
}

export function ScopeMismatchAlert({
  mismatch,
  rawQuestion,
  onEditQuestion,
  onOpenDatasetSelector
}: ScopeMismatchAlertProps) {
  return (
    <div className="border border-[#ead6b5] bg-white rounded-xl p-6 shadow-surface space-y-5">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-full bg-[#fffaf1] border border-[#ead6b5] text-[#b47a28] flex items-center justify-center shrink-0">
          <AlertCircle className="w-5 h-5" />
        </div>
        <div className="space-y-1 min-w-0">
          <h2 className="text-base font-semibold text-ink">
            Phạm vi yêu cầu chưa được hỗ trợ trong bộ dữ liệu này
          </h2>
          <p className="text-xs text-muted italic truncate">
            “{rawQuestion}”
          </p>
        </div>
      </div>

      <div className="p-4 bg-[#fffaf1] border border-[#ead6b5] rounded-lg text-xs space-y-2.5 text-[#6e5225]">
        <p className="font-semibold text-[13px]">
          {mismatch.reason || 'Yêu cầu phân tích vượt quá phạm vi dữ liệu đã kiểm định.'}
        </p>

        <div className="text-[12px] space-y-1 text-[#697481] border-t border-[#ead6b5]/60 pt-2">
          <p className="font-medium text-ink">Phạm vi sẵn sàng trong bộ dữ liệu hiện hành:</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pl-1">
            <div>• Chu kỳ hỗ trợ: <strong>{mismatch.availableCapabilitiesSummary.periods}</strong></div>
            <div>• Ngân hàng hỗ trợ: <strong>{mismatch.availableCapabilitiesSummary.entities}</strong></div>
            <div className="sm:col-span-2">• Chỉ tiêu hỗ trợ: <strong>{mismatch.availableCapabilitiesSummary.metrics}</strong></div>
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={onEditQuestion}
          className="border-line hover:bg-canvas text-xs font-semibold text-ink gap-2"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Chỉnh câu hỏi</span>
        </Button>

        <Button
          type="button"
          onClick={onOpenDatasetSelector}
          className="bg-ink hover:bg-[#263849] text-white font-semibold text-xs h-10 px-4 gap-2 shadow-xs transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Đổi nguồn dữ liệu</span>
        </Button>
      </div>
    </div>
  );
}
