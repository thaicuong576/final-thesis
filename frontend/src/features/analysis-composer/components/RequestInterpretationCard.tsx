import type { ParseResult } from '../model/types';
import { formatPeriodsSignature } from '../model/intentParser';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CheckCircle2, ArrowRight, Settings2, Check } from 'lucide-react';

interface RequestInterpretationCardProps {
  parseResult: ParseResult;
  onConfirm: () => void;
  onOpenScopeAdjustment: () => void;
  onEditQuestion: () => void;
  isConfirming?: boolean;
}

export function RequestInterpretationCard({
  parseResult,
  onConfirm,
  onOpenScopeAdjustment,
  onEditQuestion,
  isConfirming = false
}: RequestInterpretationCardProps) {
  const { rawQuestion, scope } = parseResult;
  const { selectedCapabilities } = scope.analysisPlan;

  const entityDisplay =
    scope.entities.length > 0
      ? scope.entities.map((e) => e.ticker).join(', ')
      : scope.referenceUniverseLabel || 'Toàn hệ thống';

  return (
    <div className="border border-line bg-white rounded-xl p-6 shadow-surface space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-line pb-4">
        <div className="space-y-1">
          <Badge
            variant="outline"
            className="bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3] gap-1 px-2 py-0.5 text-xs font-semibold"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-[#2f6f5e]" />
            Hệ thống hiểu yêu cầu
          </Badge>
          <h2 className="text-base font-semibold text-ink">Xác nhận kế hoạch phân tích</h2>
          <p className="text-xs text-muted italic line-clamp-2">
            “{rawQuestion}”
          </p>
        </div>

        <button
          type="button"
          onClick={onEditQuestion}
          className="text-xs font-medium text-muted hover:text-ink underline self-start shrink-0"
        >
          Nhập lại câu hỏi
        </button>
      </div>

      {/* Query-Adaptive Section 1: Phạm vi hệ thống nhận diện */}
      <div className="p-4 bg-canvas rounded-lg border border-line space-y-2">
        <span className="text-[11px] font-bold uppercase tracking-wider text-muted block">
          Phạm vi hệ thống nhận diện
        </span>
        <div className="text-sm font-semibold text-ink">
          {scope.scopeSignature}
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted pt-0.5">
          <span>
            <strong>Doanh nghiệp:</strong> {entityDisplay}
          </span>
          <span aria-hidden="true">•</span>
          <span>
            <strong>Chu kỳ:</strong>{' '}
            {formatPeriodsSignature(scope.periods)}
          </span>
          <span aria-hidden="true">•</span>
          <span>
            <strong>Chỉ tiêu:</strong>{' '}
            {scope.metrics.length > 0
              ? scope.metrics.map((m) => m.acronym).join(', ')
              : 'Không áp dụng (Bối cảnh vĩ mô)'}
          </span>
        </div>
      </div>

      {/* Query-Adaptive Section 2: Phân tích sẽ sử dụng */}
      <div className="space-y-2.5">
        <span className="text-[11px] font-bold uppercase tracking-wider text-muted block">
          Phân tích sẽ sử dụng
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {selectedCapabilities.map((cap) => (
            <div
              key={cap.id}
              className="flex items-start gap-2.5 p-3 rounded-lg bg-[#edf7f3] border border-[#bce2d3] text-xs"
            >
              <div className="mt-0.5 grid place-items-center w-4 h-4 rounded-full bg-[#2f6f5e] text-white shrink-0">
                <Check className="w-2.5 h-2.5 stroke-[3]" />
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-[#2f6f5e]">{cap.label}</div>
                {cap.description && (
                  <div className="text-[11px] text-[#2f6f5e]/80 mt-0.5">
                    {cap.description}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Action CTAs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-line">
        <Button
          type="button"
          variant="outline"
          onClick={onOpenScopeAdjustment}
          className="border-line hover:bg-canvas text-xs font-semibold text-ink gap-2 self-start sm:self-auto"
        >
          <Settings2 className="w-3.5 h-3.5 text-muted" />
          <span>Chỉnh phạm vi</span>
        </Button>

        <div className="flex items-center gap-2.5 self-end sm:self-auto">
          <Button
            type="button"
            variant="ghost"
            onClick={onEditQuestion}
            className="text-xs font-medium text-muted hover:text-ink"
          >
            Hủy
          </Button>

          <Button
            type="button"
            onClick={onConfirm}
            disabled={isConfirming}
            className="bg-[#1c5d9c] hover:bg-[#154676] text-white font-semibold text-xs h-10 px-5 gap-2 shadow-xs transition"
          >
            <span>Xác nhận & phân tích</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
