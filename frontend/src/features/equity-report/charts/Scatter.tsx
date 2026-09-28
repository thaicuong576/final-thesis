import React, { useRef } from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { fmtPeriod, niceTicks } from '@/shared/lib/formatting';
import { useChartWidth } from './useChartWidth';

export const Scatter: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const width = useChartWidth(containerRef, 560);

  const highlightSet = new Set(highlight.length > 0 ? highlight : dataset.highlight_entity_ids || []);

  const metricXId = dataset.metric_ids?.[0] || 'bank.npl_g35';
  const metricYId = dataset.metric_ids?.[1] || 'bank.llr_coverage';
  const metricX = getMetricPresentation(metricXId, metrics);
  const metricY = getMetricPresentation(metricYId, metrics);

  const rows = dataset.rows || [];
  const refLines = dataset.reference_lines || [];

  // Group by entity
  const entityMap = new Map<string, { x: number; y: number; period: string }>();
  for (const r of rows) {
    if (r.status === 'missing' || r.value === null) continue;
    if (!entityMap.has(r.entity_id)) {
      entityMap.set(r.entity_id, { x: 0, y: 0, period: r.period });
    }
    const cur = entityMap.get(r.entity_id)!;
    if (r.metric_id === metricXId) cur.x = Number(r.value);
    if (r.metric_id === metricYId) cur.y = Number(r.value);
  }

  // Medians from refLines or data
  const medianXRef = refLines.find((r) => r.metric_id === metricXId && r.kind === 'median');
  const medianYRef = refLines.find((r) => r.metric_id === metricYId && r.kind === 'median');
  const medianX = medianXRef ? Number(medianXRef.value) : null;
  const medianY = medianYRef ? Number(medianYRef.value) : null;

  // Scale ranges strictly from data (including medians), +8% padding each side, no negative truncation if data >= 0
  const xValues = Array.from(entityMap.values()).map((p) => p.x);
  if (medianX !== null && !isNaN(medianX)) xValues.push(medianX);
  const yValues = Array.from(entityMap.values()).map((p) => p.y);
  if (medianY !== null && !isNaN(medianY)) yValues.push(medianY);

  const rawMinX = xValues.length > 0 ? Math.min(...xValues) : 0;
  const rawMaxX = xValues.length > 0 ? Math.max(...xValues) : 1;
  const spanX = rawMaxX - rawMinX || (rawMaxX !== 0 ? Math.abs(rawMaxX) * 0.1 : 1);
  const padX = spanX * 0.08;
  const paddedMinX = rawMinX >= 0 ? Math.max(0, rawMinX - padX) : rawMinX - padX;
  const paddedMaxX = rawMaxX + padX;

  const rawMinY = yValues.length > 0 ? Math.min(...yValues) : 0;
  const rawMaxY = yValues.length > 0 ? Math.max(...yValues) : 1;
  const spanY = rawMaxY - rawMinY || (rawMaxY !== 0 ? Math.abs(rawMaxY) * 0.1 : 1);
  const padY = spanY * 0.08;
  const paddedMinY = rawMinY >= 0 ? Math.max(0, rawMinY - padY) : rawMinY - padY;
  const paddedMaxY = rawMaxY + padY;

  const ticksX = niceTicks(paddedMinX, paddedMaxX, 4);
  const actualMinX = ticksX[0] ?? paddedMinX;
  const actualMaxX = ticksX[ticksX.length - 1] ?? paddedMaxX;

  const ticksY = niceTicks(paddedMinY, paddedMaxY, 4);
  const actualMinY = ticksY[0] ?? paddedMinY;
  const actualMaxY = ticksY[ticksY.length - 1] ?? paddedMaxY;

  const chartW = width;
  const chartH = Math.min(280, Math.max(200, Math.round(width * 0.46)));
  const leftM = 40;
  const rightM = 24;
  const topM = 24;
  const bottomM = 28;

  const plotW = chartW - leftM - rightM;
  const plotH = chartH - topM - bottomM;

  const scaleX = (val: number) => {
    if (actualMaxX === actualMinX) return leftM + plotW / 2;
    return leftM + ((val - actualMinX) / (actualMaxX - actualMinX)) * plotW;
  };

  const scaleY = (val: number) => {
    if (actualMaxY === actualMinY) return topM + plotH / 2;
    return topM + plotH - ((val - actualMinY) / (actualMaxY - actualMinY)) * plotH;
  };

  // Label offsets heuristic to avoid overlapping
  const getOffset = (entity: string, cx: number, cy: number): { dx: number; dy: number; anchor: 'start' | 'end' | 'middle' } => {
    if (entity === 'ACB') return { dx: 6, dy: 14, anchor: 'start' };
    if (entity === 'MBB') return { dx: 8, dy: -3, anchor: 'start' };
    if (entity === 'TCB') return { dx: -8, dy: -2, anchor: 'end' };
    if (entity === 'VCB') return { dx: 8, dy: 4, anchor: 'start' };
    if (entity === 'VPB') return { dx: -8, dy: -6, anchor: 'end' };

    if (cx > leftM + plotW - 40) return { dx: -8, dy: 3, anchor: 'end' };
    if (cy < topM + 20) return { dx: 6, dy: 12, anchor: 'start' };
    return { dx: 6, dy: 3, anchor: 'start' };
  };

  return (
    <div ref={containerRef} className={`w-full max-w-[640px] my-2 ${className}`}>
      <svg
        viewBox={`0 0 ${chartW} ${chartH}`}
        width="100%"
        height={chartH}
        role="img"
        aria-label={`Biểu đồ phân tán ${metricX.shortLabel} và ${metricY.shortLabel}`}
        className="overflow-visible font-sans"
      >
        {/* Horizontal grid lines & Y labels */}
        {ticksY.map((t) => {
          const y = scaleY(t);
          return (
            <g key={`y-${t}`}>
              <line
                x1={leftM}
                x2={leftM + plotW}
                y1={y}
                y2={y}
                stroke="var(--border-subtle, #deded7)"
                strokeWidth="1"
              />
              <text
                x={leftM - 6}
                y={y + 4}
                textAnchor="end"
                fontSize="11"
                fill="var(--text-muted, #85857e)"
              >
                {t}
              </text>
            </g>
          );
        })}

        {/* X labels */}
        {ticksX.map((t) => {
          const x = scaleX(t);
          return (
            <text
              key={`x-${t}`}
              x={x}
              y={chartH - 12}
              textAnchor="middle"
              fontSize="11"
              fill="var(--text-muted, #85857e)"
            >
              {t}%
            </text>
          );
        })}

        {/* Median dashed line for X */}
        {medianX !== null && (
          <line
            x1={scaleX(medianX)}
            x2={scaleX(medianX)}
            y1={topM}
            y2={topM + plotH}
            stroke="var(--text-muted, #85857e)"
            strokeDasharray="3 3"
            strokeWidth="1"
          />
        )}

        {/* Median dashed line for Y */}
        {medianY !== null && (
          <line
            x1={leftM}
            x2={leftM + plotW}
            y1={scaleY(medianY)}
            y2={scaleY(medianY)}
            stroke="var(--text-muted, #85857e)"
            strokeDasharray="3 3"
            strokeWidth="1"
          />
        )}

        {/* Axis descriptive labels */}
        <text x={leftM} y={topM - 10} fontSize="11" fill="var(--text-muted, #85857e)">
          {metricY.shortLabel} ({metricY.unit}) ↑ dày hơn
        </text>
        <text
          x={leftM + plotW}
          y={chartH - 2}
          textAnchor="end"
          fontSize="11"
          fill="var(--text-muted, #85857e)"
        >
          {metricX.shortLabel} → cao hơn
        </text>
        <text
          x={leftM + plotW}
          y={topM - 10}
          textAnchor="end"
          fontSize="11"
          fill="var(--text-muted, #85857e)"
        >
          đường đứt: trung vị
        </text>

        {/* Scatter Points */}
        {Array.from(entityMap.entries()).map(([entity, pt]) => {
          const isHighlight = highlightSet.has(entity);
          const cx = scaleX(pt.x);
          const cy = scaleY(pt.y);
          const offset = getOffset(entity, cx, cy);
          const formattedX = formatMetricValue(pt.x, metricX);
          const formattedY = formatMetricValue(pt.y, metricY);
          const ariaLabel = `${entity} · ${metricX.shortLabel}: ${formattedX} · ${metricY.shortLabel}: ${formattedY} · ${fmtPeriod(pt.period)}`;

          return (
            <g key={entity} className="group">
              <circle
                cx={cx}
                cy={cy}
                r={isHighlight ? 5 : 3.5}
                fill={isHighlight ? 'var(--fill-accent, #ee9f0d)' : 'var(--text-secondary, #62625d)'}
                tabIndex={0}
                role="graphics-symbol"
                aria-label={ariaLabel}
                className="cursor-pointer focus:outline-none focus:stroke-text-primary focus:stroke-2 hover:r-5 transition-all"
              >
                <title>{ariaLabel}</title>
              </circle>
              <text
                x={cx + offset.dx}
                y={cy + offset.dy}
                textAnchor={offset.anchor}
                fontSize="11"
                fontFamily="var(--font-mono, monospace)"
                fontWeight={isHighlight ? '700' : '400'}
                fill={isHighlight ? 'var(--text-accent, #bc7600)' : 'var(--text-secondary, #62625d)'}
              >
                {entity}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
