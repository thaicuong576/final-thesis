import React, { useRef } from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { fmtPeriod, niceTicks, formatDecimalVi } from '@/shared/lib/formatting';
import { useChartWidth } from './useChartWidth';

export const SmallMultiples: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const width = useChartWidth(containerRef, 560);

  const highlightSet = new Set(highlight.length > 0 ? highlight : dataset.highlight_entity_ids || []);
  const targetEntity = highlightSet.size > 0 ? Array.from(highlightSet)[0] : 'ACB';

  const metricIds = dataset.metric_ids || [];
  const periods = dataset.periods || ['2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4'];
  const rows = dataset.rows || [];

  const isSingleCol = width < 480;
  const numCols = isSingleCol ? 1 : width >= 720 ? 4 : 2;
  const gap = 12;
  const cardWidth = Math.max(160, Math.floor((width - (numCols - 1) * gap) / numCols));
  const chartW = Math.max(140, cardWidth - 16);
  const chartH = 110;

  // Group all entities
  const allEntities = Array.from(new Set(rows.map((r) => r.entity_id)));
  const otherEntitiesCount = Math.max(0, allEntities.length - 1);

  // Group rows: metricId -> entityId -> period -> row
  const dataTree = new Map<string, Map<string, Map<string, (typeof rows)[0]>>>();
  for (const r of rows) {
    if (!dataTree.has(r.metric_id)) dataTree.set(r.metric_id, new Map());
    const mTree = dataTree.get(r.metric_id)!;
    if (!mTree.has(r.entity_id)) mTree.set(r.entity_id, new Map());
    mTree.get(r.entity_id)!.set(r.period, r);
  }

  const missingNotes: string[] = [];

  return (
    <div ref={containerRef} className={`w-full max-w-[640px] my-2 ${className}`}>
      <div className={`grid gap-3 ${isSingleCol ? 'grid-cols-1' : 'grid-cols-2 md:grid-cols-4'}`}>
        {metricIds.map((mId) => {
          const metricMeta = getMetricPresentation(mId, metrics);
          const mTree = dataTree.get(mId) || new Map();

          // Gather all values for this metric to calculate Y bounds
          const metricVals: number[] = [];
          for (const entTree of mTree.values()) {
            for (const r of entTree.values()) {
              if (r.status !== 'missing' && r.value !== null) {
                metricVals.push(Number(r.value));
              }
            }
          }

          const rawMin = metricVals.length > 0 ? Math.min(...metricVals) : 0;
          const rawMax = metricVals.length > 0 ? Math.max(...metricVals) : 10;
          const pad = (rawMax - rawMin) * 0.1 || 1;
          const yLo = Math.max(0, Math.floor(rawMin - pad));
          const yHi = Math.ceil(rawMax + pad);

          const ticks = niceTicks(yLo, yHi, 3);
          const actualLo = ticks[0] ?? yLo;
          const actualHi = ticks[ticks.length - 1] ?? yHi;

          // Target current value (last period)
          const lastPeriod = periods[periods.length - 1];
          const targetLastRow = mTree.get(targetEntity)?.get(lastPeriod);
          const targetLastVal = targetLastRow && targetLastRow.status !== 'missing' && targetLastRow.value !== null
            ? formatMetricValue(targetLastRow.value, metricMeta)
            : '—';

          const leftM = 36;
          const rightM = 10;
          const topM = 12;
          const bottomM = 22;
          const plotW = Math.max(20, chartW - leftM - rightM);
          const plotH = Math.max(20, chartH - topM - bottomM);

          const scaleX = (idx: number) => {
            if (periods.length <= 1) return leftM + plotW / 2;
            return leftM + (idx / (periods.length - 1)) * plotW;
          };

          const scaleY = (v: number) => {
            if (actualHi === actualLo) return topM + plotH / 2;
            return topM + plotH - ((v - actualLo) / (actualHi - actualLo)) * plotH;
          };

          return (
            <div key={mId} className="border border-line rounded p-2 bg-surface-primary">
              <div className="flex justify-between items-center text-xs mb-1">
                <span className="text-text-secondary font-medium truncate">
                  {metricMeta.shortLabel} {metricMeta.unit ? `(${metricMeta.unit})` : ''}
                </span>
                <span className="font-semibold text-text-accent font-sans tabular-nums ml-1">{targetLastVal}</span>
              </div>

              <svg
                viewBox={`0 0 ${chartW} ${chartH}`}
                width={chartW}
                height={chartH}
                role="img"
                aria-label={`Diễn biến ${metricMeta.shortLabel} qua các quý`}
                className="overflow-visible font-sans max-w-full"
              >
                {/* 3 Y Ticks */}
                {ticks.map((t) => {
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
                        x={leftM - 4}
                        y={y + 4}
                        textAnchor="end"
                        fontSize="11"
                        fill="var(--text-muted, #85857e)"
                      >
                        {formatDecimalVi(t)}
                      </text>
                    </g>
                  );
                })}

                {/* X labels (quarters) */}
                {periods.map((p, idx) => {
                  const x = scaleX(idx);
                  const shortPeriod = p.replace(/^(\d{4})_/, '').replace('_', '');
                  return (
                    <text
                      key={p}
                      x={x}
                      y={chartH - 4}
                      textAnchor="middle"
                      fontSize="11"
                      fill="var(--text-muted, #85857e)"
                    >
                      {shortPeriod}
                    </text>
                  );
                })}

                {/* Other entities lines (thin gray) */}
                {allEntities
                  .filter((e) => !highlightSet.has(e))
                  .map((e) => {
                    const eTree = mTree.get(e);
                    if (!eTree) return null;
                    const segments: Array<Array<{ x: number; y: number }>> = [];
                    let cur: Array<{ x: number; y: number }> = [];

                    periods.forEach((p, idx) => {
                      const r = eTree.get(p);
                      if (r && r.status !== 'missing' && r.value !== null) {
                        cur.push({ x: scaleX(idx), y: scaleY(Number(r.value)) });
                      } else {
                        if (cur.length > 0) {
                          segments.push(cur);
                          cur = [];
                        }
                      }
                    });
                    if (cur.length > 0) segments.push(cur);

                    return segments.map((seg, sIdx) =>
                      seg.length > 1 ? (
                        <polyline
                          key={`other-${e}-${sIdx}`}
                          points={seg.map((pt) => `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`).join(' ')}
                          fill="none"
                          stroke="var(--border-stronger, #a3a39f)"
                          strokeWidth="1"
                        />
                      ) : null
                    );
                  })}

                {/* Target Entity line & points (thick accent, breaks on missing) */}
                {(() => {
                  const targetTree = mTree.get(targetEntity);
                  if (!targetTree) return null;
                  const segments: Array<
                    Array<{ x: number; y: number; val: number; period: string; label: string }>
                  > = [];
                  let cur: Array<{ x: number; y: number; val: number; period: string; label: string }> = [];

                  periods.forEach((p, idx) => {
                    const r = targetTree.get(p);
                    if (r && r.status !== 'missing' && r.value !== null) {
                      const val = Number(r.value);
                      const formatted = formatMetricValue(val, metricMeta);
                      const label = `${targetEntity} · ${metricMeta.shortLabel}: ${formatted} · ${fmtPeriod(p)}`;
                      cur.push({ x: scaleX(idx), y: scaleY(val), val, period: p, label });
                    } else {
                      if (cur.length > 0) {
                        segments.push(cur);
                        cur = [];
                      }
                      const note = `${targetEntity} ${fmtPeriod(p)}`;
                      if (!missingNotes.includes(note)) missingNotes.push(note);
                    }
                  });
                  if (cur.length > 0) segments.push(cur);

                  return (
                    <>
                      {segments.map((seg, sIdx) =>
                        seg.length > 1 ? (
                          <polyline
                            key={`target-line-${sIdx}`}
                            points={seg.map((pt) => `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`).join(' ')}
                            fill="none"
                            stroke="var(--fill-accent, #ee9f0d)"
                            strokeWidth="2"
                          />
                        ) : null
                      )}
                      {segments.map((seg, sIdx) =>
                        seg.map((pt, pIdx) => (
                          <circle
                            key={`target-pt-${sIdx}-${pIdx}`}
                            cx={pt.x}
                            cy={pt.y}
                            r={2.5}
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
                    </>
                  );
                })()}
              </svg>
            </div>
          );
        })}
      </div>

      {/* Legend & missing note */}
      <div className="mt-2 text-[11px] text-text-muted flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          <span className="text-text-accent font-bold">━</span> {targetEntity}
        </span>
        {otherEntitiesCount > 0 && (
          <span>
            <span className="text-border-strong font-bold">━</span> {otherEntitiesCount} ngân hàng còn lại
          </span>
        )}
        {missingNotes.length > 0 && (
          <span className="italic">
            · {missingNotes.join(', ')} chưa có số liệu đã kiểm định, để trống thay vì ước tính.
          </span>
        )}
      </div>
    </div>
  );
};
