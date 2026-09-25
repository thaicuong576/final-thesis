import type { AnalysisCapabilities } from '@/entities/capability/model/types';
import { formatPeriodsSignature } from '../model/intentParser';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Database } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface ActiveDatasetCardProps {
  capabilities: AnalysisCapabilities;
}

export function ActiveDatasetCard({ capabilities }: ActiveDatasetCardProps) {
  const entityCount = capabilities.entities.length;
  const entityTickers =
    entityCount > 10
      ? `${capabilities.entities.slice(0, 10).map((e) => e.ticker).join(' · ')} … (${entityCount} NHTM)`
      : capabilities.entities.map((e) => e.ticker).join(' · ');
  const periodSig = formatPeriodsSignature(capabilities.periods);
  const metricCount = capabilities.metrics.length;
  const metricAcronyms = capabilities.metrics.map((m) => m.acronym).join(' · ');

  return (
    <div className="border border-line bg-card rounded-md px-4 py-2.5 min-h-[72px] flex flex-col justify-center gap-1.5 transition-colors">
      {/* Top line: Status, Title, and Switch Button */}
      <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
        <div className="flex min-w-0 flex-1 flex-col items-start gap-2 sm:flex-row sm:items-center">
          <div className="flex min-w-0 items-center gap-2">
          <div className={`flex items-center justify-center w-4 h-4 rounded-full shrink-0 ${capabilities.analysis_available === true ? 'bg-ready text-white' : 'bg-warning-soft text-warning'}`}>
            <Database className="w-2.5 h-2.5 stroke-[2]" aria-hidden="true" />
          </div>
          <h2 className="text-sm font-bold text-ink tracking-tight">
            Phạm vi dữ liệu API công bố
          </h2>
          </div>
          <Badge
            variant="outline"
            title={capabilities.analysis_available === true ? capabilities.dataset_snapshot_id || capabilities.snapshotId || undefined : capabilities.snapshotId || undefined}
            className="max-w-full whitespace-normal break-all bg-surface-secondary text-ink-secondary border-border-subtle px-1.5 py-0 text-[10px] font-semibold shrink-0 sm:max-w-[240px] sm:truncate"
          >
            {capabilities.analysis_available === true && capabilities.dataset_snapshot_id
              ? `Snapshot: ${capabilities.dataset_snapshot_id}`
              : `Snapshot đã kiểm định: chưa có · Catalog: ${capabilities.snapshotId || 'chưa công bố'}`}
          </Badge>
        </div>

        <Button asChild variant="outline" size="sm" className="shrink-0 self-start h-7 px-2.5 text-xs font-semibold text-ink hover:bg-surface-hover border-border-subtle">
          <Link to="/data">Xem phạm vi</Link>
        </Button>
      </div>

      {/* Catalog scope, as reported by the API. */}
      <div className="flex flex-wrap items-center gap-x-2 text-xs text-ink-secondary">
        <div className="inline-flex items-center gap-1">
          <span className="font-semibold text-ink">{entityCount} ngân hàng</span>
          <span className="text-[11px] font-mono text-ink-secondary">({entityTickers})</span>
        </div>
        <span aria-hidden="true" className="text-border-strong">•</span>
        <div className="inline-flex items-center gap-1 font-mono text-[11px] text-ink font-medium">
          <span>{periodSig || 'Kỳ chưa công bố'}</span>
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
