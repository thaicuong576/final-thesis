import React, { useState, useMemo } from 'react';
import type { ChartProps } from './types';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { formatDisplayText } from '@/shared/lib/formatting';

export const RankHeatmap: React.FC<ChartProps> = ({ dataset, metrics, highlight = [], className = '' }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const { highlightSet, metricIds, entities, displayedEntities, cellMap, medianMap, totalEntities } = useMemo(() => {
    const rawHighlight = highlight.length > 0 ? highlight : dataset.highlight_entity_ids || [];
    const hlSet = new Set(rawHighlight);
    const rws = dataset.rows || [];
    const mIds = (dataset.metric_ids && dataset.metric_ids.length > 0)
      ? dataset.metric_ids
      : Array.from(new Set(rws.map((r) => r.metric_id).filter(Boolean)));
    const rLines = dataset.reference_lines || [];

    const eSet = new Set<string>();
    for (const r of rws) eSet.add(r.entity_id);
    const ents = Array.from(eSet);

    const sorted = [
      ...ents.filter((e) => hlSet.has(e)),
      ...ents.filter((e) => !hlSet.has(e))
    ];

    const cMap = new Map<string, (typeof rws)[0]>();
    for (const r of rws) {
      cMap.set(`${r.entity_id}:${r.metric_id}`, r);
    }

    const medMap = new Map<string, number>();
    for (const ref of rLines) {
      if (ref.kind === 'median') {
        medMap.set(ref.metric_id, Number(ref.value));
      }
    }
    for (const mId of mIds) {
      if (!medMap.has(mId)) {
        const vals = rws
          .filter((r) => r.metric_id === mId && r.status !== 'missing' && r.value !== null)
          .map((r) => Number(r.value))
          .sort((a, b) => a - b);
        if (vals.length > 0) {
          const mid = Math.floor(vals.length / 2);
          const med = vals.length % 2 !== 0 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2;
          medMap.set(mId, med);
        }
      }
    }

    let disp = sorted;
    if (!isExpanded && ents.length > 5) {
      const visible = new Set<string>();
      for (const e of ents) {
        if (hlSet.has(e)) visible.add(e);
      }
      if (visible.size === 0 && sorted.length > 0) {
        visible.add(sorted[0]);
      }
      for (const mId of mIds) {
        let bestEntity: string | null = null;
        let worstEntity: string | null = null;
        let bestRank = Infinity;
        let worstRank = -1;

        for (const e of ents) {
          const row = cMap.get(`${e}:${mId}`);
          if (row && row.status !== 'missing' && row.value !== null && row.rank_better !== null && row.rank_better !== undefined) {
            if (row.rank_better < bestRank) {
              bestRank = row.rank_better;
              bestEntity = e;
            }
            if (row.rank_better > worstRank) {
              worstRank = row.rank_better;
              worstEntity = e;
            }
          }
        }
        if (bestEntity) visible.add(bestEntity);
        if (worstEntity) visible.add(worstEntity);
      }
      disp = sorted.filter((e) => visible.has(e));
    }

    return {
      highlightSet: hlSet,
      metricIds: mIds,
      entities: ents,
      displayedEntities: disp,
      cellMap: cMap,
      medianMap: medMap,
      totalEntities: ents.length || 5
    };
  }, [dataset, highlight, isExpanded]);

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
      <table className="w-full min-w-[420px] border-collapse text-xs table-fixed font-sans" role="table" aria-label="Ma trận vị thế nhóm ngân hàng">
        <thead>
          <tr className="border-b border-line text-text-muted">
            <th className="py-2 px-2 text-left font-semibold w-[24%]">Ngân hàng</th>
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
          {displayedEntities.map((entity) => {
            const isHighlight = highlightSet.has(entity);

            return (
              <tr key={entity} className={isHighlight ? 'bg-amber-soft/25 font-semibold ring-1 ring-inset ring-amber/40' : ''}>
                <td className={`py-2 px-2 text-left font-mono ${isHighlight ? 'text-text-primary font-bold' : 'text-text-secondary'}`}>
                  <span>{entity}</span>
                  {isHighlight && (
                    <span className="ml-1.5 text-[10px] px-1 py-0.2 rounded bg-amber-soft text-amber-border font-sans font-semibold uppercase">
                      Mục tiêu
                    </span>
                  )}
                </td>
                {metricIds.map((mId) => {
                  const meta = getMetricPresentation(mId, metrics);
                  const row = cellMap.get(`${entity}:${mId}`);
                  const isMissing = !row || row.status === 'missing' || row.value === null;
                  const rank = row?.rank_better;
                  const bg = isMissing ? 'transparent' : getCellBg(rank, meta.direction);
                  // Missing values never shown as 0!
                  const displayVal = isMissing ? '—' : formatMetricValue(row.value, meta);

                  return (
                    <td
                      key={mId}
                      style={{ background: bg }}
                      className="py-2 px-1 text-right font-mono text-xs transition-colors"
                    >
                      <span className={isMissing ? 'text-text-muted font-normal' : ''}>{displayVal}</span>
                      {rank !== null && rank !== undefined && (
                        <span className="ml-1 inline-flex items-center px-1 py-0.2 rounded text-[10px] font-mono font-medium bg-surface-secondary/90 text-text-secondary border border-border-subtle select-none">
                          #{rank}
                        </span>
                      )}
                      {isMissing && row?.missing_reason && (
                        <span className="block text-[10px] text-text-warning italic leading-tight truncate max-w-[120px]" title={row.missing_reason}>
                          {formatDisplayText(row.missing_reason)}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}

          {/* Median row */}
          <tr className="border-t-2 border-line text-text-primary font-semibold bg-surface-secondary/40">
            <td className="py-2 px-2 text-left text-text-secondary font-medium">Trung vị</td>
            {metricIds.map((mId) => {
              const meta = getMetricPresentation(mId, metrics);
              const med = medianMap.get(mId);
              return (
                <td key={mId} className="py-2 px-1 text-right font-mono text-xs text-text-primary">
                  {med !== undefined ? formatMetricValue(med, meta) : '—'}
                </td>
              );
            })}
          </tr>
        </tbody>
      </table>

      {/* Collapse / Expand toggle */}
      {entities.length > 5 && (
        <div className="mt-2.5 flex items-center justify-between text-[11px] text-text-muted print:hidden">
          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="text-[12px] font-medium text-text-accent hover:underline cursor-pointer bg-transparent border-none p-0 inline-flex items-center gap-1"
          >
            {isExpanded ? 'Thu gọn danh sách' : `Xem đủ ${entities.length} ngân hàng`}
          </button>
          {!isExpanded && (
            <span>
              Đang hiển thị {displayedEntities.length}/{entities.length} ngân hàng (mục tiêu & cực trị)
            </span>
          )}
        </div>
      )}

      {/* Legend / explanation */}
      <div className="mt-2 text-[11px] text-text-muted">
        Xanh: tốt hơn nhóm, đỏ: kém hơn nhóm (theo hạng). Nợ xấu: thấp là tốt.
      </div>
    </div>
  );
};
