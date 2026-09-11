import { useState } from 'react';
import type { AnalysisCapabilities } from '@/entities/capability/model/types';
import type { AnalyticalCapabilityId, AnalyticalCapabilityItem, ParsedScope } from '../model/types';
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
  onApplyScope: (updatedScope: ParsedScope) => void;
}

export function ScopeAdjustmentDrawer({
  open,
  onOpenChange,
  capabilities,
  currentScope,
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
  const [selectedCapabilityIds, setSelectedCapabilityIds] = useState<AnalyticalCapabilityId[]>(
    currentScope.analysisPlan.selectedCapabilities.map((c) => c.id)
  );

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

  function toggleCapability(id: AnalyticalCapabilityId) {
    setSelectedCapabilityIds((prev) =>
      prev.includes(id) ? (prev.length > 1 ? prev.filter((item) => item !== id) : prev) : [...prev, id]
    );
  }

  function handleSave() {
    const nextEntities = capabilities.entities.filter((e) => selectedEntityIds.includes(e.id));
    const nextPeriods = capabilities.periods.filter((p) => selectedPeriodIds.includes(p.id));
    const nextMetrics = capabilities.metrics.filter((m) => selectedMetricIds.includes(m.id));

    // Rebuild capability items
    const allPossibleCapabilities: AnalyticalCapabilityItem[] = [
      {
        id: 'company',
        label: 'Phân tích doanh nghiệp',
        description: `Phân tích dữ liệu tài chính của ${nextEntities.map((e) => e.ticker).join(', ')}`,
        selected: selectedCapabilityIds.includes('company')
      },
      {
        id: 'peer',
        label: 'Nhóm tham chiếu',
        description: `Đối sánh cùng kỳ với ${capabilities.peerUniverse.label}`,
        selected: selectedCapabilityIds.includes('peer')
      },
      {
        id: 'macro',
        label: 'Bối cảnh vĩ mô',
        description: 'Tích hợp diễn biến chính sách tiền tệ và tăng trưởng tín dụng',
        selected: selectedCapabilityIds.includes('macro')
      }
    ];

    const nextSelectedCapabilities = allPossibleCapabilities.filter((c) => c.selected);

    const entitySig = nextEntities.map((e) => e.ticker).join(' · ');
    const periodSig =
      nextPeriods.length === 4
        ? 'Q1–Q4/2024'
        : nextPeriods.map((p) => `Q${p.quarter}/${p.year}`).join(', ');
    const metricSig = nextMetrics.map((m) => m.acronym).join(' · ');
    const scopeSignature = [entitySig, periodSig, metricSig].filter(Boolean).join(' · ');

    onApplyScope({
      ...currentScope,
      entities: nextEntities,
      periods: nextPeriods,
      metrics: nextMetrics,
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
              Công cụ hiệu chỉnh thứ cấp khi bạn muốn điều chỉnh kết quả bóc tách tự động.
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-5 text-xs">
            {/* Analytical Capabilities (Query-Adaptive Toggles) */}
            <div className="space-y-2">
              <label className="font-semibold text-ink block">
                Khả năng phân tích sử dụng
              </label>
              <div className="space-y-1.5">
                {[
                  { id: 'company' as const, label: 'Phân tích doanh nghiệp' },
                  { id: 'peer' as const, label: 'Nhóm tham chiếu' },
                  { id: 'macro' as const, label: 'Bối cảnh vĩ mô' }
                ].map((cap) => {
                  const isSelected = selectedCapabilityIds.includes(cap.id);
                  return (
                    <button
                      key={cap.id}
                      type="button"
                      onClick={() => toggleCapability(cap.id)}
                      className={`w-full p-2.5 rounded-md border text-left text-xs transition flex items-center justify-between ${
                        isSelected
                          ? 'border-[#1c5d9c] bg-[#f5f8fb] text-ink font-semibold'
                          : 'border-line bg-white text-muted hover:border-slate-400'
                      }`}
                    >
                      <span>{cap.label}</span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-[#1c5d9c]" />}
                    </button>
                  );
                })}
              </div>
            </div>

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
                      className={`px-3 py-1.5 rounded-md border text-xs font-semibold transition ${
                        isSelected
                          ? 'border-[#1c5d9c] bg-[#f5f8fb] text-[#1c5d9c]'
                          : 'border-line bg-white text-muted hover:border-slate-400'
                      }`}
                    >
                      {isSelected && '✓ '}
                      {entity.ticker}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Periods */}
            <div className="space-y-2">
              <label className="font-semibold text-ink block">
                Chu kỳ thời gian ({selectedPeriodIds.length})
              </label>
              <div className="flex flex-wrap gap-1.5">
                {capabilities.periods.map((period) => {
                  const isSelected = selectedPeriodIds.includes(period.id);
                  return (
                    <button
                      key={period.id}
                      type="button"
                      onClick={() => togglePeriod(period.id)}
                      className={`px-3 py-1.5 rounded-md border text-xs font-semibold transition ${
                        isSelected
                          ? 'border-[#1c5d9c] bg-[#f5f8fb] text-[#1c5d9c]'
                          : 'border-line bg-white text-muted hover:border-slate-400'
                      }`}
                    >
                      {isSelected && '✓ '}
                      Q{period.quarter}/{period.year}
                    </button>
                  );
                })}
              </div>
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
