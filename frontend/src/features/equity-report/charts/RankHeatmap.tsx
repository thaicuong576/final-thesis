import React from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';

export const RankHeatmap: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
  const highlightSet = new Set(highlight.length > 0 ? highlight : dataset.highlight_entity_ids || []);

  const metricIds = dataset.metric_ids || [];
  const rows = dataset.rows || [];
  const refLines = dataset.reference_lines || [];

  // Group entities
  const entitySet = new Set<string>();
  for (const r of rows) entitySet.add(r.entity_id);
  const entities = Array.from(entitySet);

  // Highlight entities sorted to top, then remaining
  const sortedEntities = [
    ...entities.filter((e) => highlightSet.has(e)),
    ...entities.filter((e) => !highlightSet.has(e))
  ];

  const totalEntities = entities.length || 5;

  // Row map: entity -> metric -> row
  const cellMap = new Map<string, (typeof rows)[0]>();
  for (const r of rows) {
    cellMap.set(`${r.entity_id}:${r.metric_id}`, r);
  }

  // Median map: metric -> value
  const medianMap = new Map<string, number>();
  for (const ref of refLines) {
    if (ref.kind === 'median') {
      medianMap.set(ref.metric_id, Number(ref.value));
    }
  }

  // If median missing for any metric, calculate median from valid rows
  for (const mId of metricIds) {
    if (!medianMap.has(mId)) {
      const vals = rows
        .filter((r) => r.metric_id === mId && r.status !== 'missing' && r.value !== null)
        .map((r) => Number(r.value))
        .sort((a, b) => a - b);
      if (vals.length > 0) {
        const mid = Math.floor(vals.length / 2);
        const med = vals.length % 2 !== 0 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2;
        medianMap.set(mId, med);
      }
    }
  }

  // Tint calculation
  const getCellBg = (rank: number | null | undefined, direction: string) => {
    if (direction === 'neutral' || rank === null || rank === undefined) {
      return 'transparent';
    }
    if (rank === 1) {
      return 'color-mix(in srgb, var(--success, #2f9e62) 40%, transparent)';
    }
    if (rank === 2) {
      return 'color-mix(in srgb, var(--success, #2f9e62) 18%, transparent)';
    }
    if (rank === totalEntities) {
      return 'color-mix(in srgb, var(--danger, #c84b3f) 36%, transparent)';
    }
    if (rank === totalEntities - 1 && totalEntities > 3) {
      return 'color-mix(in srgb, var(--danger, #c84b3f) 18%, transparent)';
    }
    return 'transparent';
  };

  return (
    <div className={`my-2 overflow-x-auto ${className}`}>
      <table className="w-full border-collapse text-xs table-fixed font-sans" role="table">
        <thead>
          <tr className="border-b border-line text-text-muted">
            <th className="py-2 px-2 text-left font-semibold w-[22%]"></th>
            {metricIds.map((mId) => {
              const meta = getMetricPresentation(mId, metrics);
              return (
                <th key={mId} className="py-2 px-1 text-right font-semibold text-[11px]">
                  {meta.shortLabel}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {sortedEntities.map((entity) => {
            const isHighlight = highlightSet.has(entity);

            return (
              <tr key={entity} className={isHighlight ? 'font-semibold' : ''}>
                <td className={`py-2 px-2 text-left font-mono ${isHighlight ? 'text-text-primary' : 'text-text-secondary'}`}>
                  {entity}
                </td>
                {metricIds.map((mId) => {
                  const meta = getMetricPresentation(mId, metrics);
                  const row = cellMap.get(`${entity}:${mId}`);
                  const isMissing = !row || row.status === 'missing' || row.value === null;
                  const rank = row?.rank_better;
                  const bg = isMissing ? 'transparent' : getCellBg(rank, meta.direction);
                  const displayVal = isMissing ? '—' : formatMetricValue(row.value, meta);

                  return (
                    <td
                      key={mId}
                      style={{ background: bg }}
                      className="py-2 px-1 text-right font-mono text-xs transition-colors"
                    >
                      <span>{displayVal}</span>
                      {rank !== null && rank !== undefined && (
                        <span className="text-text-muted text-[11px] font-sans"> #{rank}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}

          {/* Median row */}
          <tr className="border-t border-line text-text-secondary font-medium">
            <td className="py-2 px-2 text-left text-text-muted">Trung vị</td>
            {metricIds.map((mId) => {
              const meta = getMetricPresentation(mId, metrics);
              const med = medianMap.get(mId);
              return (
                <td key={mId} className="py-2 px-1 text-right font-mono text-xs text-text-muted">
                  {med !== undefined ? formatMetricValue(med, meta) : '—'}
                </td>
              );
            })}
          </tr>
        </tbody>
      </table>

      {/* Legend / explanation */}
      <div className="mt-2 text-[11px] text-text-muted">
        Xanh: tốt hơn nhóm, đỏ: kém hơn nhóm (theo hạng). Nợ xấu: thấp là tốt.
      </div>
    </div>
  );
};
