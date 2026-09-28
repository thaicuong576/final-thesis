import React from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { fmtPeriod } from '@/shared/lib/formatting';

export const KpiStrip: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
  const highlightSet = new Set(highlight.length > 0 ? highlight : dataset.highlight_entity_ids || []);
  const rows = dataset.rows || [];

  return (
    <div className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 my-2 ${className}`}>
      {rows.map((row, idx) => {
        const isHighlight = highlightSet.has(row.entity_id);
        const metricMeta = getMetricPresentation(row.metric_id, metrics);
        const isMissing = row.status === 'missing' || row.value === null;
        const displayVal = isMissing ? '—' : formatMetricValue(row.value, metricMeta);
        const sub = row.rank_better !== null && row.rank_better !== undefined
          ? `Hạng ${row.rank_better} · ${fmtPeriod(row.period)}`
          : fmtPeriod(row.period);

        const ariaLabel = isMissing
          ? `${row.entity_id} · ${metricMeta.shortLabel}: chưa có số liệu đã kiểm định · ${fmtPeriod(row.period)}`
          : `${row.entity_id} · ${metricMeta.shortLabel}: ${displayVal} · ${fmtPeriod(row.period)}`;

        return (
          <div
            key={`${row.entity_id}-${row.metric_id}-${row.period}-${idx}`}
            tabIndex={0}
            role="region"
            aria-label={ariaLabel}
            className={`p-3 rounded border transition-colors ${
              isHighlight
                ? 'border-accent bg-amber-soft/20 text-text-primary'
                : 'border-line bg-surface-secondary text-text-secondary'
            } focus:outline-none focus:ring-2 focus:ring-accent`}
            title={ariaLabel}
          >
            <div className="text-xs font-medium text-text-secondary flex justify-between items-center">
              <span>{metricMeta.shortLabel}</span>
              <span className="font-mono text-[11px] font-semibold">{row.entity_id}</span>
            </div>
            <div className="text-2xl font-bold tracking-tight text-text-primary my-1">
              {displayVal}
            </div>
            <div className="text-[11px] text-text-muted truncate">
              {isMissing ? (
                <span className="text-warning-text">{row.missing_reason || 'Chưa có số liệu đã kiểm định'}</span>
              ) : (
                sub
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
