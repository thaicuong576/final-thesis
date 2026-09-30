import React from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';

export const ComparisonTable: React.FC<ChartProps> = ({ dataset, metrics, className = '' }) => {
  const metricIds = dataset.metric_ids || [];
  const rows = dataset.rows || [];

  // Group entities in order of appearance
  const entitySet = new Set<string>();
  for (const r of rows) entitySet.add(r.entity_id);
  const entities = Array.from(entitySet);

  // Group rows: metricId -> entityId -> row
  const cellMap = new Map<string, (typeof rows)[0]>();
  for (const r of rows) {
    cellMap.set(`${r.metric_id}:${r.entity_id}`, r);
  }

  return (
    <div className={`my-2 overflow-x-auto ${className}`}>
      <table className="w-full min-w-[340px] border-collapse text-xs table-fixed font-sans" role="table">
        <thead>
          <tr className="border-b border-line text-text-muted">
            <th className="py-2 px-2 text-left font-semibold w-[35%]"></th>
            {entities.map((entity) => (
              <th key={entity} className="py-2 px-2 text-right font-mono font-semibold text-sm text-text-primary">
                {entity}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {metricIds.map((mId) => {
            const meta = getMetricPresentation(mId, metrics);

            // Determine which entity is better for this metric
            const validCells = entities
              .map((entity) => ({ entity, row: cellMap.get(`${mId}:${entity}`) }))
              .filter((c) => c.row && c.row.status !== 'missing' && c.row.value !== null);

            let bestEntity: string | null = null;

            if (validCells.length > 1 && meta.direction !== 'neutral') {
              // First check if rank_better is present
              const rank1 = validCells.find((c) => c.row?.rank_better === 1);
              if (rank1) {
                bestEntity = rank1.entity;
              } else {
                // Otherwise calculate by direction
                if (meta.direction === 'lower_is_better') {
                  const sorted = [...validCells].sort((a, b) => Number(a.row!.value) - Number(b.row!.value));
                  if (Number(sorted[0].row!.value) < Number(sorted[1].row!.value)) {
                    bestEntity = sorted[0].entity;
                  }
                } else {
                  const sorted = [...validCells].sort((a, b) => Number(b.row!.value) - Number(a.row!.value));
                  if (Number(sorted[0].row!.value) > Number(sorted[1].row!.value)) {
                    bestEntity = sorted[0].entity;
                  }
                }
              }
            }

            return (
              <tr key={mId}>
                <td className="py-2 px-2 text-left font-medium text-text-secondary">
                  {meta.shortLabel}
                </td>
                {entities.map((entity) => {
                  const row = cellMap.get(`${mId}:${entity}`);
                  const isMissing = !row || row.status === 'missing' || row.value === null;
                  const isBest = entity === bestEntity;
                  const displayVal = isMissing ? '—' : formatMetricValue(row.value, meta);

                  return (
                    <td
                      key={entity}
                      className={`py-2 px-2 text-right font-mono text-xs ${
                        isBest ? 'font-semibold text-text-primary' : 'text-text-secondary'
                      }`}
                    >
                      <span>{displayVal}</span>
                      {isBest && (
                        <span aria-label="tốt hơn" className="ml-1 text-text-primary select-none">
                          ▲
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Footnote */}
      <div className="mt-2 text-[11px] text-text-muted">
        ▲ tốt hơn theo chiều của chỉ tiêu (nợ xấu: thấp là tốt).
      </div>
    </div>
  );
};
