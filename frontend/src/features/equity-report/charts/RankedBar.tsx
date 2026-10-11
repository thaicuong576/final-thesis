import React, { useRef } from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { fmtPeriod } from '@/shared/lib/formatting';
import { useChartWidth } from './useChartWidth';
import { useSafeEquityReport } from '../components/useEquityReport';

export const RankedBar: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const width = useChartWidth(containerRef, 560);
  const equityCtx = useSafeEquityReport();
  const onOpenFact = equityCtx?.onOpenFact;
  const facts = equityCtx?.facts || [];

  const highlightList = highlight.length > 0 ? highlight : dataset.highlight_entity_ids || [];
  const primaryHighlight = highlightList[0];
  const secondaryHighlights = new Set(highlightList.slice(1));

  const metricMeta = getMetricPresentation(dataset.metric_ids?.[0] || '', metrics);

  const rawRows = dataset.rows || [];
  const validRows = rawRows.filter((r) => r.status !== 'missing' && r.value !== null);
  const missingRows = rawRows.filter((r) => r.status === 'missing' || r.value === null);

  // Sorted by value descending
  const sortedRows = [...validRows].sort((a, b) => Number(b.value) - Number(a.value));

  // Determine median value from reference lines or data
  const medianRef = dataset.reference_lines?.find((ref) => ref.kind === 'median');
  const medianVal = medianRef ? Number(medianRef.value) : null;

  // Maximum value for scaling (axis starts strictly from 0)
  const maxValue = Math.max(
    ...sortedRows.map((r) => Number(r.value)),
    medianVal !== null ? medianVal : 0,
    1
  );

  const rowHeight = 24;
  const barHeight = 14;
  const leftMargin = 42;
  const rightMargin = 65; // space for value labels
  const topMargin = 14;
  const chartWidth = width;
  const availableBarWidth = Math.max(10, chartWidth - leftMargin - rightMargin);

  const totalHeight = Math.min(320, topMargin + sortedRows.length * rowHeight + 20);

  // Scale function: value 0 maps to leftMargin, maxValue maps to leftMargin + availableBarWidth
  const scaleX = (val: number) => {
    if (val <= 0) return leftMargin;
    return leftMargin + (val / maxValue) * availableBarWidth;
  };

  const medianX = medianVal !== null ? scaleX(medianVal) : null;

  return (
    <div ref={containerRef} className={`w-full max-w-[640px] my-2 ${className}`}>
      <svg
        viewBox={`0 0 ${chartWidth} ${totalHeight}`}
        width="100%"
        height={totalHeight}
        role="img"
        aria-label={`Biểu đồ xếp hạng ${metricMeta.shortLabel}`}
        className="overflow-visible font-sans"
      >
        {/* Median reference line */}
        {medianX !== null && (() => {
          const medianFactId =
            medianRef?.fact_id ||
            facts.find((f) => f.fact_type === 'peer_median' && f.metric_id === (dataset.metric_ids?.[0] || medianRef?.metric_id))?.fact_id;

          return (
            <g
              className={`median-line ${medianFactId && onOpenFact ? 'cursor-pointer hover:opacity-80' : ''}`}
              onClick={() => {
                if (medianFactId && onOpenFact) {
                  onOpenFact(medianFactId);
                }
              }}
            >
              <title>{medianFactId ? `Trung vị nhóm: ${formatMetricValue(medianVal, metricMeta)} (Nhấp để xem nguồn gốc)` : undefined}</title>
              <line
                x1={medianX}
                x2={medianX}
                y1={4}
                y2={totalHeight - 14}
                stroke="var(--text-muted, #85857e)"
                strokeDasharray="3 3"
                strokeWidth="1"
              />
              <text
                x={medianX}
                y={totalHeight - 2}
                textAnchor="middle"
                fontSize="11"
                fill="var(--text-muted, #85857e)"
              >
                trung vị
              </text>
            </g>
          );
        })()}

        {/* Rows */}
        {sortedRows.map((row, idx) => {
          const isPrimary = row.entity_id === primaryHighlight;
          const isSecondary = secondaryHighlights.has(row.entity_id);
          const isHighlight = isPrimary || isSecondary;

          const barFill = isPrimary
            ? 'var(--fill-accent, #ee9f0d)'
            : isSecondary
            ? 'var(--text-secondary, #52524e)'
            : 'var(--border-stronger, #a3a39f)';

          const labelFill = isPrimary
            ? 'var(--text-accent, #bc7600)'
            : isSecondary
            ? 'var(--text-primary, #20201e)'
            : 'var(--text-secondary, #62625d)';

          const y = topMargin + idx * rowHeight;
          const val = Number(row.value);
          const barW = Math.max(scaleX(val) - leftMargin, 2);
          const formattedVal = formatMetricValue(val, metricMeta);

          const matchedFact =
            facts.find((f) => f.entity_id === row.entity_id && f.metric_id === (dataset.metric_ids?.[0] || row.metric_id) && f.period === row.period && f.fact_type === 'value') ||
            facts.find((f) => f.entity_id === row.entity_id && f.metric_id === (dataset.metric_ids?.[0] || row.metric_id) && f.period === row.period) ||
            facts.find((f) => row.observation_id && f.input_observation_ids?.includes(row.observation_id));
          const factId = matchedFact?.fact_id;
          const ariaLabel = `${row.entity_id} · ${metricMeta.shortLabel}: ${formattedVal} · ${fmtPeriod(row.period)}${factId ? ' (Nhấp để xem nguồn gốc)' : ''}`;

          return (
            <g key={`${row.entity_id}-${idx}`} className="group">
              {/* Entity Label */}
              <text
                x={leftMargin - 6}
                y={y + barHeight - 2}
                textAnchor="end"
                fontSize="11"
                fontFamily="var(--font-mono, monospace)"
                fontWeight={isHighlight ? '700' : '400'}
                fill={labelFill}
              >
                {row.entity_id}
              </text>

              {/* Bar (Starts strictly from 0 / leftMargin) */}
              <rect
                x={leftMargin}
                y={y}
                width={barW}
                height={barHeight}
                rx={2}
                fill={barFill}
                tabIndex={0}
                role="graphics-symbol"
                aria-label={ariaLabel}
                onClick={() => {
                  if (factId && onOpenFact) {
                    onOpenFact(factId);
                  }
                }}
                className={`focus:outline-none focus:stroke-accent focus:stroke-2 transition-opacity ${
                  factId && onOpenFact ? 'cursor-pointer hover:opacity-85' : 'cursor-pointer hover:opacity-90'
                }`}
              >
                <title>{ariaLabel}</title>
              </rect>

              {/* Value Text */}
              <text
                x={leftMargin + barW + 5}
                y={y + barHeight - 2}
                fontSize="11"
                fontWeight={isHighlight ? '700' : '400'}
                fill="var(--text-primary, #20201e)"
                onClick={() => {
                  if (factId && onOpenFact) {
                    onOpenFact(factId);
                  }
                }}
                className={factId && onOpenFact ? 'cursor-pointer hover:fill-accent transition-colors' : ''}
              >
                {formattedVal}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Note for missing rows */}
      {missingRows.length > 0 && (
        <div className="mt-1 text-[11px] text-text-muted italic">
          {missingRows.map((r, i) => (
            <span key={i}>
              {r.entity_id} {fmtPeriod(r.period)} chưa có số liệu đã kiểm định.
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
