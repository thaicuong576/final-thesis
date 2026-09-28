import React from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { fmtPeriod } from '@/shared/lib/formatting';

export const RankedBar: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
  const highlightSet = new Set(highlight.length > 0 ? highlight : dataset.highlight_entity_ids || []);
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

  const rowHeight = 22;
  const barHeight = 13;
  const leftMargin = 38;
  const rightMargin = 55; // space for value labels
  const topMargin = 12;
  const chartWidth = 320;
  const availableBarWidth = chartWidth - leftMargin - rightMargin;

  const totalHeight = topMargin + sortedRows.length * rowHeight + 14;

  // Scale function: value 0 maps to leftMargin, maxValue maps to leftMargin + availableBarWidth
  const scaleX = (val: number) => {
    if (val <= 0) return leftMargin;
    return leftMargin + (val / maxValue) * availableBarWidth;
  };

  const medianX = medianVal !== null ? scaleX(medianVal) : null;

  return (
    <div className={`my-2 ${className}`}>
      <svg
        viewBox={`0 0 ${chartWidth} ${totalHeight}`}
        width="100%"
        role="img"
        aria-label={`Biểu đồ xếp hạng ${metricMeta.shortLabel}`}
        className="overflow-visible font-sans"
      >
        {/* Median reference line */}
        {medianX !== null && (
          <g className="median-line">
            <line
              x1={medianX}
              x2={medianX}
              y1={2}
              y2={totalHeight - 8}
              stroke="var(--text-muted, #85857e)"
              strokeDasharray="3 3"
              strokeWidth="1"
            />
            <text
              x={medianX}
              y={totalHeight - 1}
              textAnchor="middle"
              fontSize="9"
              fill="var(--text-muted, #85857e)"
            >
              trung vị
            </text>
          </g>
        )}

        {/* Rows */}
        {sortedRows.map((row, idx) => {
          const isHighlight = highlightSet.has(row.entity_id);
          const y = topMargin + idx * rowHeight;
          const val = Number(row.value);
          const barW = Math.max(scaleX(val) - leftMargin, 2);
          const formattedVal = formatMetricValue(val, metricMeta);
          const ariaLabel = `${row.entity_id} · ${metricMeta.shortLabel}: ${formattedVal} · ${fmtPeriod(row.period)}`;

          return (
            <g key={`${row.entity_id}-${idx}`} className="group">
              {/* Entity Label */}
              <text
                x={leftMargin - 6}
                y={y + barHeight - 2}
                textAnchor="end"
                fontSize="11"
                fontFamily="var(--font-mono, monospace)"
                fontWeight={isHighlight ? '600' : '400'}
                fill={isHighlight ? 'var(--text-accent, #bc7600)' : 'var(--text-secondary, #62625d)'}
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
                fill={isHighlight ? 'var(--fill-accent, #ee9f0d)' : 'var(--border-stronger, #a3a39f)'}
                tabIndex={0}
                role="graphics-symbol"
                aria-label={ariaLabel}
                className="cursor-pointer focus:outline-none focus:stroke-accent focus:stroke-2 hover:opacity-90 transition-opacity"
              >
                <title>{ariaLabel}</title>
              </rect>

              {/* Value Text */}
              <text
                x={leftMargin + barW + 5}
                y={y + barHeight - 2}
                fontSize="11"
                fontWeight={isHighlight ? '600' : '400'}
                fill={isHighlight ? 'var(--text-primary, #20201e)' : 'var(--text-primary, #20201e)'}
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
