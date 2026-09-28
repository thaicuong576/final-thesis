import React from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { fmtPeriod, niceTicks } from '@/shared/lib/formatting';

export const Scatter: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
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

  // Scale ranges
  const xValues = Array.from(entityMap.values()).map((p) => p.x);
  if (medianX !== null) xValues.push(medianX);
  const yValues = Array.from(entityMap.values()).map((p) => p.y);
  if (medianY !== null) yValues.push(medianY);

  const minX = Math.max(0, Math.floor(Math.min(...xValues, 0.5)));
  const maxX = Math.ceil(Math.max(...xValues, 4.5));
  const minY = Math.max(0, Math.floor((Math.min(...yValues, 40) - 20) / 20) * 20);
  const maxY = Math.ceil((Math.max(...yValues, 220) + 20) / 50) * 50;

  const ticksX = niceTicks(minX, maxX, 4);
  const actualMinX = ticksX[0] ?? minX;
  const actualMaxX = ticksX[ticksX.length - 1] ?? maxX;

  const ticksY = niceTicks(minY, maxY, 4);
  const actualMinY = ticksY[0] ?? minY;
  const actualMaxY = ticksY[ticksY.length - 1] ?? maxY;

  const chartW = 320;
  const chartH = 220;
  const leftM = 36;
  const rightM = 16;
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
  const getOffset = (entity: string): { dx: number; dy: number; anchor: 'start' | 'end' | 'middle' } => {
    switch (entity) {
      case 'ACB':
        return { dx: 6, dy: 14, anchor: 'start' };
      case 'MBB':
        return { dx: 8, dy: -3, anchor: 'start' };
      case 'TCB':
        return { dx: -8, dy: -2, anchor: 'end' };
      case 'VCB':
        return { dx: 8, dy: 4, anchor: 'start' };
      case 'VPB':
        return { dx: -8, dy: -6, anchor: 'end' };
      default:
        return { dx: 6, dy: 3, anchor: 'start' };
    }
  };

  return (
    <div className={`my-2 ${className}`}>
      <svg
        viewBox={`0 0 ${chartW} ${chartH}`}
        width="100%"
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
                fontSize="10"
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
              fontSize="10"
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
        <text x={leftM} y={topM - 10} fontSize="10" fill="var(--text-muted, #85857e)">
          {metricY.shortLabel} ({metricY.unit}) ↑ dày hơn
        </text>
        <text
          x={leftM + plotW}
          y={chartH - 2}
          textAnchor="end"
          fontSize="10"
          fill="var(--text-muted, #85857e)"
        >
          {metricX.shortLabel} → cao hơn
        </text>
        <text
          x={leftM + plotW}
          y={topM - 10}
          textAnchor="end"
          fontSize="10"
          fill="var(--text-muted, #85857e)"
        >
          đường đứt: trung vị
        </text>

        {/* Scatter Points */}
        {Array.from(entityMap.entries()).map(([entity, pt]) => {
          const isHighlight = highlightSet.has(entity);
          const cx = scaleX(pt.x);
          const cy = scaleY(pt.y);
          const offset = getOffset(entity);
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
