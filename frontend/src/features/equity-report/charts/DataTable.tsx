import React from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { fmtPeriod, formatDisplayText } from '@/shared/lib/formatting';
import { RankHeatmap } from './RankHeatmap';
import { useSafeEquityReport } from '../components/useEquityReport';

export const DataTable: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
  const equityCtx = useSafeEquityReport();
  const onOpenFact = equityCtx?.onOpenFact;
  const facts = equityCtx?.facts || [];
  const rows = dataset.rows || [];

  // Pivot long datasets (shape peer_table / comparison_table or > 12 rows) into compact matrix
  if (rows.length > 12 || dataset.shape === 'peer_table' || (dataset.shape === 'comparison_table' && rows.length > 12)) {
    return <RankHeatmap dataset={dataset} metrics={metrics} highlight={highlight} className={className} />;
  }

  const highlightSet = new Set(highlight.length > 0 ? highlight : dataset.highlight_entity_ids || []);

  return (
    <div className={`overflow-x-auto my-2 border border-line rounded bg-surface-primary p-3 ${className}`}>
      <table className="w-full min-w-[420px] text-xs text-left border-collapse" role="table">
        <thead>
          <tr className="border-b border-line text-text-tertiary font-semibold">
            <th className="py-1.5 px-2">Thực thể</th>
            <th className="py-1.5 px-2">Chỉ tiêu</th>
            <th className="py-1.5 px-2">Kỳ</th>
            <th className="py-1.5 px-2 text-right">Giá trị</th>
            <th className="py-1.5 px-2 text-right">Hạng</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row, idx) => {
            const isHighlight = highlightSet.has(row.entity_id);
            const metricMeta = getMetricPresentation(row.metric_id, metrics);
            const isMissing = row.status === 'missing' || row.value === null;
            const displayVal = isMissing ? '—' : formatMetricValue(row.value, metricMeta);
            const rankText = row.rank_better !== null && row.rank_better !== undefined ? `#${row.rank_better}` : '—';

            const matchedFact =
              facts.find((f) => f.entity_id === row.entity_id && f.metric_id === row.metric_id && f.period === row.period && f.fact_type === 'value') ||
              facts.find((f) => f.entity_id === row.entity_id && f.metric_id === row.metric_id && f.period === row.period) ||
              facts.find((f) => row.observation_id && f.input_observation_ids?.includes(row.observation_id));
            const factId = matchedFact?.fact_id;

            return (
              <tr
                key={`${row.entity_id}-${row.metric_id}-${row.period}-${idx}`}
                className={isHighlight ? 'bg-amber-soft/20 font-semibold' : ''}
              >
                <td className="py-1.5 px-2 font-mono">{row.entity_id}</td>
                <td className="py-1.5 px-2">{metricMeta.shortLabel}</td>
                <td className="py-1.5 px-2 text-text-secondary">{fmtPeriod(row.period)}</td>
                <td
                  className={`py-1.5 px-2 text-right font-medium ${
                    !isMissing && factId && onOpenFact ? 'cursor-pointer hover:text-text-accent transition-colors' : ''
                  }`}
                  onClick={() => {
                    if (!isMissing && factId && onOpenFact) {
                      onOpenFact(factId);
                    }
                  }}
                  title={!isMissing && factId ? 'Xem nguồn gốc số liệu' : undefined}
                >
                  {isMissing ? (
                    <span className="text-warning-text font-normal italic text-[11px]" title={row.missing_reason || undefined}>
                      {formatDisplayText(row.missing_reason) || 'Chưa có số liệu'}
                    </span>
                  ) : (
                    displayVal
                  )}
                </td>
                <td className="py-1.5 px-2 text-right text-text-secondary">{rankText}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {dataset.reference_lines && dataset.reference_lines.length > 0 && (
        <div className="mt-2 pt-2 border-t border-line text-[11px] text-text-secondary flex flex-wrap gap-3">
          {dataset.reference_lines.map((ref, idx) => {
            const metricMeta = getMetricPresentation(ref.metric_id, metrics);
            const label = ref.kind === 'median' ? 'Trung vị' : ref.kind;
            const refFactId =
              ref.fact_id ||
              facts.find((f) => f.fact_type === (ref.kind === 'median' ? 'peer_median' : ref.kind) && f.metric_id === ref.metric_id && f.period === ref.period)?.fact_id;

            return (
              <span
                key={idx}
                className={refFactId && onOpenFact ? 'cursor-pointer hover:text-text-accent transition-colors' : ''}
                onClick={() => {
                  if (refFactId && onOpenFact) {
                    onOpenFact(refFactId);
                  }
                }}
                title={refFactId ? 'Xem nguồn gốc số liệu' : undefined}
              >
                {label} ({metricMeta.shortLabel} {fmtPeriod(ref.period)}):{' '}
                <strong className="text-text-primary">{formatMetricValue(ref.value, metricMeta)}</strong>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
};
