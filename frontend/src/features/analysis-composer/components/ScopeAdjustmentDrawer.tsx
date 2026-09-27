import { useState } from 'react';
import type { AnalysisCapabilities } from '@/entities/capability/model/types';
import type { ParsedScope } from '../model/types';
import {
  formatPeriodsSignature,
  planAnalyticalCapabilities
} from '../model/intentParser';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Settings2, Check } from 'lucide-react';

interface ScopeAdjustmentDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  capabilities: AnalysisCapabilities;
  currentScope: ParsedScope;
  rawQuestion?: string;
  onApplyScope: (updatedScope: ParsedScope) => void;
}

export function ScopeAdjustmentDrawer({
  open,
  onOpenChange,
  capabilities,
  currentScope,
  rawQuestion,
  onApplyScope
}: ScopeAdjustmentDrawerProps) {
  const [selectedEntityIds, setSelectedEntityIds] = useState<string[]>(
    currentScope.entities.map((e) => e.id)
  );
  const [selectedPeriodIds, setSelectedPeriodIds] = useState<string[]>(
    currentScope.periods.map((p) => p.id)
  );
  const [selectedMetricIds, setSelectedMetricIds] = useState<string[]>(
    currentScope.metrics.map((m) => m.id)
  );

  const isPeerActive = currentScope.analysisPlan.selectedCapabilities.some((c) => c.id === 'peer');

  function toggleEntity(id: string) {
    setSelectedEntityIds((prev) =>
      prev.includes(id) ? (prev.length > 1 ? prev.filter((item) => item !== id) : prev) : [...prev, id]
    );
  }

  function togglePeriod(id: string) {
    setSelectedPeriodIds((prev) =>
      prev.includes(id) ? (prev.length > 1 ? prev.filter((item) => item !== id) : prev) : [...prev, id]
    );
  }

  function toggleMetric(id: string) {
    setSelectedMetricIds((prev) =>
      prev.includes(id) ? (prev.length > 1 ? prev.filter((item) => item !== id) : prev) : [...prev, id]
    );
  }

  function handleSave() {
    const nextEntities = capabilities.entities.filter((e) => selectedEntityIds.includes(e.id));
    const nextPeriods = capabilities.periods.filter((p) => selectedPeriodIds.includes(p.id));
    const nextMetrics = capabilities.metrics.filter((m) => selectedMetricIds.includes(m.id));

    const effectiveRawQuestion = rawQuestion || currentScope.rawQuestion || '';

    // Replan freshly using preserved rawQuestion and adjusted business scope without sticky flags
    const nextSelectedCapabilities = planAnalyticalCapabilities({
      entities: nextEntities,
      capabilities,
      rawQuestion: effectiveRawQuestion
    });

    const nextIsPeerActive = nextSelectedCapabilities.some((c) => c.id === 'peer');
    const isMacroOnly =
      nextSelectedCapabilities.length === 1 && nextSelectedCapabilities[0].id === 'macro';

    const entitySig =
      nextEntities.length > 0
        ? nextEntities.map((e) => e.ticker).join(' · ')
        : nextIsPeerActive
        ? capabilities.peerUniverse?.label || 'Toàn ngành'
        : isMacroOnly
        ? 'Toàn hệ thống'
        : '';
    const periodSig = formatPeriodsSignature(nextPeriods);
    const metricSig = isMacroOnly ? '' : nextMetrics.map((m) => m.acronym).join(' · ');
    const scopeSignature = [entitySig, periodSig, metricSig].filter(Boolean).join(' · ');

    onApplyScope({
      ...currentScope,
      rawQuestion: effectiveRawQuestion,
      entities: nextEntities,
      periods: nextPeriods,
      metrics: isMacroOnly ? [] : nextMetrics,
      scopeSignature,
      analysisPlan: {
        selectedCapabilities: nextSelectedCapabilities
      }
    });
    onOpenChange(false);
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-md bg-white p-6 flex flex-col justify-between overflow-y-auto"
      >
        <div className="space-y-6">
          <SheetHeader className="text-left space-y-1 pb-2 border-b border-line">
            <SheetTitle className="text-base font-semibold text-ink flex items-center gap-2">
              <Settings2 className="w-4 h-4 text-muted" />
              <span>Chỉnh phạm vi phân tích</span>
            </SheetTitle>
            <SheetDescription className="text-xs text-muted">
              Công cụ hiệu chỉnh thứ cấp khi bạn muốn điều chỉnh kết quả bóc tách tự động. Hệ thống sẽ tự động xác định các năng lực phân tích tương ứng.
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-5 text-xs">
            {/* Entities */}
            <div className="space-y-2">
              <label className="font-semibold text-ink block">
                Doanh nghiệp phân tích ({selectedEntityIds.length})
              </label>
              <div className="flex flex-wrap gap-1.5">
                {capabilities.entities.map((entity) => {
                  const isSelected = selectedEntityIds.includes(entity.id);
                  return (
                    <button
                      key={entity.id}
                      type="button"
                      onClick={() => toggleEntity(entity.id)}
                      className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-md border text-xs font-semibold transition ${
                        isSelected
                          ? 'border-[#1c5d9c] bg-[#f5f8fb] text-[#1c5d9c]'
                          : 'border-line bg-white text-muted hover:border-slate-400'
                      }`}
                    >
                      {isSelected && <Check className="size-3.5 stroke-[2]" />}
                      <span>{entity.ticker}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Contextual Peer Universe (read-only disclosure if Peer analysis is part of plan) */}
            {isPeerActive && capabilities.peerUniverse && (
              <div className="space-y-1.5 p-3 rounded-lg bg-canvas border border-line">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-ink">Nhóm tham chiếu liên kết</span>
                  <span className="text-[10px] text-muted font-medium">Cố định theo bộ dữ liệu</span>
                </div>
                <div className="text-xs font-semibold text-ink">
                  {capabilities.peerUniverse.label}
                </div>
                <p className="text-[11px] text-muted leading-relaxed">
                  {capabilities.peerUniverse.description}
                </p>
              </div>
            )}

            {/* Periods */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-ink block">
                  Chu kỳ thời gian ({selectedPeriodIds.length})
                </label>
                <span className="text-[10px] text-ink-tertiary font-mono">Chỉ hỗ trợ kỳ quý</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {capabilities.periods.map((period) => {
                  const isSelected = selectedPeriodIds.includes(period.id);
                  return (
                    <button
                      key={period.id}
                      type="button"
                      onClick={() => togglePeriod(period.id)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs font-semibold transition ${
                        isSelected
                          ? 'border-[#1c5d9c] bg-[#f5f8fb] text-[#1c5d9c]'
                          : 'border-line bg-white text-muted hover:border-slate-400'
                      }`}
                      title={`Mã kỳ snapshot: ${period.id}`}
                    >
                      {isSelected && <Check className="size-3.5 stroke-[2]" />}
                      <span className="font-mono">Q{period.quarter}/{period.year}</span>
                      <span className="text-[10px] opacity-75 font-mono">({period.id})</span>
                    </button>
                  );
                })}
              </div>
              <p className="text-[11px] text-muted">
                Snapshot chỉ lưu các quan sát theo từng quý (ví dụ: <code>2024_Q4</code>). Vui lòng chọn kỳ quý thay vì kỳ gộp cả năm.
              </p>
            </div>

            {/* Metrics */}
            <div className="space-y-2">
              <label className="font-semibold text-ink block">
                Chỉ tiêu tài chính ({selectedMetricIds.length})
              </label>
              <div className="flex flex-col gap-1.5">
                {capabilities.metrics.map((metric) => {
                  const isSelected = selectedMetricIds.includes(metric.id);
                  return (
                    <button
                      key={metric.id}
                      type="button"
                      onClick={() => toggleMetric(metric.id)}
                      className={`p-2.5 rounded-md border text-left text-xs transition flex items-center justify-between ${
                        isSelected
                          ? 'border-[#1c5d9c] bg-[#f5f8fb] text-ink font-semibold'
                          : 'border-line bg-white text-muted hover:border-slate-400'
                      }`}
                    >
                      <span>
                        <strong className="text-ink">{metric.acronym}</strong> — {metric.label}
                      </span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-[#1c5d9c]" />}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        <SheetFooter className="pt-4 border-t border-line mt-6 flex-row gap-2 sm:justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="flex-1 sm:flex-none border-line text-xs font-semibold"
          >
            Hủy
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            className="flex-1 sm:flex-none bg-[#1c5d9c] text-white hover:bg-[#154676] text-xs font-semibold"
          >
            Lưu thay đổi
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
