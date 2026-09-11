import type { AnalysisCapabilities } from '@/entities/capability/model/types';
import { formatPeriodsSignature } from '../model/intentParser';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Database, Check } from 'lucide-react';

interface ActiveDatasetCardProps {
  capabilities: AnalysisCapabilities;
  onOpenSelector: () => void;
}

export function ActiveDatasetCard({ capabilities, onOpenSelector }: ActiveDatasetCardProps) {
  const entityTickers = capabilities.entities.map((e) => e.ticker).join(' · ');
  const metricAcronyms = capabilities.metrics.map((m) => m.acronym).join(' · ');
  const periodSig = formatPeriodsSignature(capabilities.periods);

  return (
    <div className="border border-line bg-white rounded-lg p-4 shadow-surface">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Database className="w-3.5 h-3.5 text-muted" aria-hidden="true" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
              Nguồn dữ liệu
            </span>
            <Badge
              variant="outline"
              className="bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3] gap-1 px-1.5 py-0.5 text-[10px] font-semibold"
            >
              <Check className="w-3 h-3 text-[#2f6f5e]" />
              Sẵn sàng
            </Badge>
          </div>

          <h2 className="text-sm font-semibold text-ink">Ngân hàng Việt Nam 2024</h2>

          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted">
            <span className="font-medium text-ink">{entityTickers}</span>
            {periodSig && (
              <>
                <span aria-hidden="true">•</span>
                <span>{periodSig}</span>
              </>
            )}
            <span aria-hidden="true">•</span>
            <span>{metricAcronyms}</span>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onOpenSelector}
          className="self-start sm:self-center shrink-0 border-line hover:border-slate-400 hover:bg-[#f7fafc] text-xs font-semibold text-ink"
        >
          Đổi nguồn dữ liệu
        </Button>
      </div>
    </div>
  );
}
