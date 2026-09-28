import React from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { fmtPeriod, niceTicks } from '@/shared/lib/formatting';

export const GroupedBar: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
  const highlightSet = new Set(highlight.length > 0 ? highlight : dataset.highlight_entity_ids || []);

  const metricIds = dataset.metric_ids || [];
  const rows = dataset.rows || [];

  // Entities (up to 3)
  const entitySet = new Set<string>();
  for (const r of rows) entitySet.add(r.entity_id);
  const entities = Array.from(entitySet).slice(0, 3);

  // Group rows: metricId -> entityId -> row
  const cellMap = new Map<string, (typeof rows)[0]>();
  for (const r of rows) {
    cellMap.set(`${r.metric_id}:${r.entity_id}`, r);
  }

  // Find max value across all cells (axis starts from 0)
  const values = rows
    .filter((r) => r.status !== 'missing' && r.value !== null)
    .map((r) => Number(r.value));
  const maxVal = Math.max(...values, 1);

  const ticksY = niceTicks(0, Math.ceil(maxVal * 1.15), 3);
  const actualMaxY = ticksY[ticksY.length - 1] || maxVal;

  const chartW = 320;
  const chartH = 140;
  const leftM = 32;
  const rightM = 16;
  const topM = 16;
  const bottomM = 24;

  const plotW = chartW - leftM - rightM;
  const plotH = chartH - topM - bottomM;

  const numClusters = metricIds.length || 1;
  const clusterWidth = plotW / numClusters;
  const barWidth = Math.min(22, (clusterWidth - 12) / Math.max(1, entities.length));

  const scaleY = (v: number) => {
    if (actualMaxY === 0) return topM + plotH;
    return topM + plotH - (v / actualMaxY) * plotH;
  };

  return (
    <div className={`my-2 ${className}`}>
      <svg
        viewBox={`0 0 ${chartW} ${chartH}`}
        width="100%"
        role="img"
        aria-label="Biểu đồ cột so sánh theo chỉ tiêu"
        className="overflow-visible font-sans"
      >
        {/* Y Grid lines & ticks */}
        {ticksY.map((t) => {
          const y = scaleY(t);
          return (
            <g key={t}>
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
                y={y + 3}
                textAnchor="end"
                fontSize="9"
                fill="var(--text-muted, #85857e)"
              >
                {t}
              </text>
            </g>
          );
        })}

        {/* Clusters */}
        {metricIds.map((mId, cIdx) => {
          const meta = getMetricPresentation(mId, metrics);
          const clusterX = leftM + cIdx * clusterWidth;
          const clusterCenter = clusterX + clusterWidth / 2;

          return (
            <g key={mId}>
              {/* Metric Label below */}
              <text
                x={clusterCenter}
                y={chartH - 6}
                textAnchor="middle"
                fontSize="10"
                fontWeight="500"
                fill="var(--text-secondary, #62625d)"
              >
                {meta.shortLabel}
              </text>

              {/* Bars for each entity in cluster */}
              {entities.map((entity, eIdx) => {
                const row = cellMap.get(`${mId}:${entity}`);
                if (!row || row.status === 'missing' || row.value === null) return null;

                const val = Number(row.value);
                const isHighlight = highlightSet.has(entity);
                const barX = clusterCenter - (entities.length * barWidth) / 2 + eIdx * barWidth;
                const barY = scaleY(val);
                const barH = topM + plotH - barY;
                const formatted = formatMetricValue(val, meta);
                const ariaLabel = `${entity} · ${meta.shortLabel}: ${formatted} · ${fmtPeriod(row.period)}`;

                return (
                  <g key={entity} className="group">
                    <rect
                      x={barX}
                      y={barY}
                      width={Math.max(barWidth - 2, 2)}
                      height={Math.max(barH, 1)}
                      rx={2}
                      fill={isHighlight ? 'var(--fill-accent, #ee9f0d)' : 'var(--border-stronger, #a3a39f)'}
                      tabIndex={0}
                      role="graphics-symbol"
                      aria-label={ariaLabel}
                      className="cursor-pointer focus:outline-none focus:stroke-text-primary focus:stroke-2"
                    >
                      <title>{ariaLabel}</title>
                    </rect>
                    {/* Value text above bar */}
                    <text
                      x={barX + (barWidth - 2) / 2}
                      y={barY - 3}
                      textAnchor="middle"
                      fontSize="9"
                      fontWeight={isHighlight ? '600' : '400'}
                      fill="var(--text-primary, #20201e)"
                    >
                      {formatted}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>

      {/* Legend for entities */}
      <div className="mt-2 text-[11px] text-text-muted flex justify-center gap-4">
        {entities.map((entity) => {
          const isHighlight = highlightSet.has(entity);
          return (
            <span key={entity} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-sm inline-block"
                style={{
                  background: isHighlight ? 'var(--fill-accent, #ee9f0d)' : 'var(--border-stronger, #a3a39f)'
                }}
              />
              <span className={isHighlight ? 'font-semibold text-text-primary font-mono' : 'font-mono'}>
                {entity}
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
};
