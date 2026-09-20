import type { AnalysisCapabilities } from '@/entities/capability/model/types';
import { formatPeriodsSignature } from '../model/intentParser';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Check } from 'lucide-react';

export interface ActiveDatasetCardProps {
  capabilities: AnalysisCapabilities;
  onOpenSelector: () => void;
}

export function ActiveDatasetCard({ capabilities, onOpenSelector }: ActiveDatasetCardProps) {
  const entityCount = capabilities.entities.length;
  const entityTickers = capabilities.entities.map((e) => e.ticker).join(' · ');
  const periodSig = formatPeriodsSignature(capabilities.periods);
  const metricCount = capabilities.metrics.length;
  const metricAcronyms = capabilities.metrics.map((m) => m.acronym).join(' · ');

  return (
    <div className="border border-line bg-card rounded-md px-4 py-2.5 min-h-[72px] flex flex-col justify-center gap-1.5 transition-colors">
      {/* Top line: Status, Title, and Switch Button */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center justify-center w-4 h-4 rounded-full bg-ready text-white shrink-0">
            <Check className="w-2.5 h-2.5 stroke-[3]" />
          </div>
          <h2 className="text-sm font-bold text-ink tracking-tight truncate">
            Ngân hàng Việt Nam 2024
          </h2>
          <Badge
            variant="outline"
            className="bg-[#e4f4ea] text-[#2f9e62] border-[#2f9e62]/30 px-1.5 py-0 text-[10px] font-semibold shrink-0"
          >
            Sẵn sàng
          </Badge>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onOpenSelector}
          aria-label="Đổi nguồn dữ liệu"
          className="shrink-0 h-7 px-2.5 text-xs font-semibold text-ink hover:text-ink hover:bg-surface-hover border-border-subtle"
        >
          Đổi dữ liệu
        </Button>
      </div>

      {/* Bottom line: Scannable grouped metadata: 5 ngân hàng · Q1-Q4/2024 · 4 chỉ tiêu */}
      <div className="flex flex-wrap items-center gap-x-2 text-xs text-ink-secondary">
        <div className="inline-flex items-center gap-1">
          <span className="font-semibold text-ink">{entityCount} ngân hàng</span>
          <span className="text-[11px] font-mono text-ink-secondary">({entityTickers})</span>
        </div>
        <span aria-hidden="true" className="text-border-strong">•</span>
        <div className="inline-flex items-center gap-1 font-mono text-[11px] text-ink font-medium">
          <span>{periodSig || 'Q1–Q4/2024'}</span>
        </div>
        <span aria-hidden="true" className="text-border-strong">•</span>
        <div className="inline-flex items-center gap-1">
          <span className="font-semibold text-ink">{metricCount} chỉ tiêu</span>
          <span className="text-[11px] font-mono text-ink-secondary">({metricAcronyms})</span>
        </div>
      </div>
    </div>
  );
}

export const ActiveDatasetContextCard = ActiveDatasetCard;
