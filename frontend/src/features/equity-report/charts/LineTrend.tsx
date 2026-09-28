import React, { useRef } from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { fmtPeriod, niceTicks } from '@/shared/lib/formatting';
import { useChartWidth } from './useChartWidth';

export const LineTrend: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const width = useChartWidth(containerRef, 560);

  const highlightSet = new Set(highlight.length > 0 ? highlight : dataset.highlight_entity_ids || []);
  const metricMeta = getMetricPresentation(dataset.metric_ids?.[0] || '', metrics);

  const periods = dataset.periods || [];
  const rows = dataset.rows || [];
  const refLines = dataset.reference_lines || [];

  // Group rows by period for quick lookup
  const rowMap = new Map<string, (typeof rows)[0]>();
  for (const r of rows) {
    rowMap.set(`${r.entity_id}:${r.period}`, r);
  }

  // Median lookup per period
  const medianMap = new Map<string, number>();
  for (const ref of refLines) {
    if (ref.kind === 'median') {
      medianMap.set(ref.period, Number(ref.value));
    }
  }

  // Determine main entity to highlight
  const targetEntity = highlightSet.size > 0
    ? Array.from(highlightSet)[0]
    : rows[0]?.entity_id || '';

  // Gather values to determine Y scale
  const allValues: number[] = [];
  for (const r of rows) {
    if (r.status !== 'missing' && r.value !== null) {
      allValues.push(Number(r.value));
    }
  }
  for (const v of medianMap.values()) {
    allValues.push(v);
  }

  const minVal = allValues.length > 0 ? Math.min(...allValues) : 0;
  const maxVal = allValues.length > 0 ? Math.max(...allValues) : 10;
  const yPadding = (maxVal - minVal) * 0.15 || 1;
  const yMin = Math.max(0, Math.floor(minVal - yPadding));
  const yMax = Math.ceil(maxVal + yPadding);

  const ticks = niceTicks(yMin, yMax, 3);
  const actualYMin = ticks[0] ?? yMin;
  const actualYMax = ticks[ticks.length - 1] ?? yMax;

  const chartWidth = width;
  const chartHeight = Math.min(220, Math.max(140, Math.round(width * 0.32)));
  const leftMargin = 38;
  const rightMargin = 95; // space for end labels
  const topMargin = 22;
  const bottomMargin = 22;

  const plotWidth = Math.max(10, chartWidth - leftMargin - rightMargin);
  const plotHeight = chartHeight - topMargin - bottomMargin;

  const scaleX = (index: number) => {
    if (periods.length <= 1) return leftMargin + plotWidth / 2;
    return leftMargin + (index / (periods.length - 1)) * plotWidth;
  };

  const scaleY = (val: number) => {
    if (actualYMax === actualYMin) return topMargin + plotHeight / 2;
    return topMargin + plotHeight - ((val - actualYMin) / (actualYMax - actualYMin)) * plotHeight;
  };

  // Build contiguous segments for target entity (breaks at missing periods)
  const segments: Array<Array<{ x: number; y: number; val: number; period: string; label: string }>> = [];
  let currentSegment: Array<{ x: number; y: number; val: number; period: string; label: string }> = [];
  const missingPoints: string[] = [];

  periods.forEach((period, idx) => {
    const row = rowMap.get(`${targetEntity}:${period}`);
    if (row && row.status !== 'missing' && row.value !== null) {
      const val = Number(row.value);
      const x = scaleX(idx);
      const y = scaleY(val);
      const formatted = formatMetricValue(val, metricMeta);
      const label = `${targetEntity} · ${metricMeta.shortLabel}: ${formatted} · ${fmtPeriod(period)}`;
      currentSegment.push({ x, y, val, period, label });
    } else {
      if (currentSegment.length > 0) {
        segments.push(currentSegment);
        currentSegment = [];
      }
      missingPoints.push(fmtPeriod(period));
    }
  });
  if (currentSegment.length > 0) {
    segments.push(currentSegment);
  }

  // Median points
  const medianPoints: Array<{ x: number; y: number; val: number; period: string }> = [];
  periods.forEach((period, idx) => {
    if (medianMap.has(period)) {
      const val = medianMap.get(period)!;
      medianPoints.push({
        x: scaleX(idx),
        y: scaleY(val),
        val,
        period
      });
    }
  });

  const lastTargetPoint = segments[segments.length - 1]?.[segments[segments.length - 1].length - 1];
  const lastMedianPoint = medianPoints[medianPoints.length - 1];

  return (
    <div ref={containerRef} className={`w-full max-w-[640px] my-2 ${className}`}>
      <svg
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        width="100%"
        height={chartHeight}
        role="img"
        aria-label={`Biểu đồ diễn biến ${metricMeta.shortLabel} của ${targetEntity}`}
        className="overflow-visible font-sans"
      >
        {/* Y Axis Unit Label */}
        <text
          x={leftMargin}
          y={topMargin - 8}
          fontSize="11"
          fill="var(--text-muted, #85857e)"
        >
          {metricMeta.shortLabel} ({metricMeta.unit})
        </text>

        {/* Horizontal grid lines & Y labels */}
        {ticks.map((t) => {
          const y = scaleY(t);
          return (
            <g key={t} className="grid-line">
              <line
                x1={leftMargin}
                x2={leftMargin + plotWidth}
                y1={y}
                y2={y}
                stroke="var(--border-subtle, #deded7)"
                strokeWidth="1"
              />
              <text
                x={leftMargin - 6}
                y={y + 3}
                textAnchor="end"
                fontSize="11"
                fill="var(--text-muted, #85857e)"
              >
                {t}
              </text>
            </g>
          );
        })}

        {/* X axis labels (Periods) */}
        {periods.map((p, idx) => {
          const x = scaleX(idx);
          const shortPeriod = p.replace(/^(\d{4})_/, '').replace('_', '');
          return (
            <text
              key={p}
              x={x}
              y={chartHeight - 4}
              textAnchor="middle"
              fontSize="11"
              fill="var(--text-muted, #85857e)"
            >
              {shortPeriod}
            </text>
          );
        })}

        {/* Median dashed trend line */}
        {medianPoints.length > 1 && (
          <polyline
            points={medianPoints.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')}
            fill="none"
            stroke="var(--border-stronger, #a3a39f)"
            strokeWidth="1.5"
            strokeDasharray="4 3"
          />
        )}

        {/* Target Entity line segments (strictly broken across missing periods) */}
        {segments.map((seg, sIdx) => {
          if (seg.length > 1) {
            return (
              <polyline
                key={`seg-${sIdx}`}
                points={seg.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')}
                fill="none"
                stroke="var(--fill-accent, #ee9f0d)"
                strokeWidth="2"
              />
            );
          }
          return null;
        })}

        {/* Target Entity points */}
        {segments.map((seg, sIdx) =>
          seg.map((pt, pIdx) => (
            <circle
              key={`pt-${sIdx}-${pIdx}`}
              cx={pt.x}
              cy={pt.y}
              r={3}
              fill="var(--fill-accent, #ee9f0d)"
              tabIndex={0}
              role="graphics-symbol"
              aria-label={pt.label}
              className="cursor-pointer focus:outline-none focus:stroke-text-primary focus:stroke-2"
            >
              <title>{pt.label}</title>
            </circle>
          ))
        )}

        {/* End of line label for Target Entity */}
        {lastTargetPoint && (
          <text
            x={leftMargin + plotWidth + 6}
            y={lastTargetPoint.y + 3}
            fontSize="11"
            fontWeight="700"
            fill="var(--text-accent, #bc7600)"
          >
            {targetEntity} {formatMetricValue(lastTargetPoint.val, metricMeta)}
          </text>
        )}

        {/* End of line label for Median */}
        {lastMedianPoint && (
          <text
            x={leftMargin + plotWidth + 6}
            y={lastMedianPoint.y + (Math.abs(lastMedianPoint.y - (lastTargetPoint?.y || 0)) < 14 ? 15 : 3)}
            fontSize="11"
            fill="var(--text-muted, #85857e)"
          >
            trung vị {formatMetricValue(lastMedianPoint.val, metricMeta)}
          </text>
        )}
      </svg>

      {/* Note for missing periods */}
      {missingPoints.length > 0 && (
        <div className="mt-1 text-[11px] text-text-muted italic">
          {targetEntity} {missingPoints.join(', ')} chưa có số liệu đã kiểm định, để trống thay vì ước tính.
        </div>
      )}
    </div>
  );
};
