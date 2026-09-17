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
    <div className="border border-line bg-card rounded-md p-4 transition-colors">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2">
            <Database className="w-3.5 h-3.5 text-ink-secondary" aria-hidden="true" />
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-ink-secondary">
              Bộ dữ liệu hoạt động
            </span>
            <Badge
              variant="outline"
              className="bg-[#e4f4ea] text-[#2f9e62] border-[#2f9e62]/30 gap-1 px-1.5 py-0.5 text-[10px] font-semibold"
            >
              <Check className="w-3 h-3 text-[#2f9e62]" />
              Sẵn sàng
            </Badge>
          </div>

          <h2 className="text-sm font-bold text-ink tracking-tight">Ngân hàng Việt Nam 2024</h2>

          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-ink-secondary">
            <span className="font-semibold text-ink">{entityTickers}</span>
            {periodSig && (
              <>
                <span aria-hidden="true" className="text-border-strong">•</span>
                <span className="font-mono text-[11px]">{periodSig}</span>
              </>
            )}
            <span aria-hidden="true" className="text-border-strong">•</span>
            <span className="font-mono text-[11px] text-ink-secondary">{metricAcronyms}</span>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onOpenSelector}
          className="self-start sm:self-center shrink-0 text-xs font-semibold"
        >
          Đổi nguồn dữ liệu
        </Button>
      </div>
    </div>
  );
}
