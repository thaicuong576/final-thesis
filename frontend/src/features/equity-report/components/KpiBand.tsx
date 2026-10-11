import React from 'react';
import { useEquityReport } from './useEquityReport';
import { formatMetricValue, getMetricPresentation } from '../model/metricRegistry';
import { fmtPp } from '@/shared/lib/formatting';

/**
 * Headline figures for the focus bank, built only from the report's sourced facts: the value,
 * its gap to the peer median (coloured by the metric's good direction) and its rank in the group.
 * Metrics without a value fact are left out rather than filled from elsewhere.
 */
export const KpiBand: React.FC = () => {
  const { report, facts, metrics, highlight } = useEquityReport();
  const entity =
    highlight[0] ||
    (report as { target_ticker?: string }).target_ticker ||
    facts.find((f) => f.fact_type === 'value' && f.entity_id)?.entity_id;
  if (!entity) return null;

  const anchor = facts
    .filter((f) => f.fact_type === 'value' && f.entity_id === entity)
    .map((f) => f.period)
    .sort()
    .pop();
  if (!anchor) return null;

  // Metric order follows the dataset catalogue; no metric ids are hard-coded here.
  const order = Array.from(
    new Set([
      ...(metrics || []).map((m) => m.id),
      ...facts.filter((f) => f.fact_type === 'value' && f.entity_id === entity).map((f) => f.metric_id)
    ])
  );
  const cells = order.map((metricId) => {
    const at = (type: string, extra?: (f: (typeof facts)[number]) => boolean) =>
      facts.find(
        (f) => f.fact_type === type && f.metric_id === metricId && f.period === anchor && (extra ? extra(f) : true)
      );
    const value = at('value', (f) => f.entity_id === entity);
    if (!value) return null;
    const meta = getMetricPresentation(metricId, metrics);
    const median = at('peer_median');
    const gapFact = at('gap_to_median', (f) => f.entity_id === entity);
    const gap =
      gapFact?.value ?? (median && value.value !== null && median.value !== null ? Number(value.value) - Number(median.value) : null);
    const rank = at('peer_rank', (f) => f.entity_id === entity);
    const spread = at('spread') || facts.find((f) => f.fact_type === 'spread' && f.metric_id === metricId);
    const lowerBetter = meta.direction === 'lower_is_better';
    const good = gap === null || Math.abs(Number(gap)) < 0.005 ? null : lowerBetter ? Number(gap) < 0 : Number(gap) > 0;
    return { metricId, meta, value, gap, good, rank, median, spread };
  }).filter(Boolean) as Array<{
    metricId: string;
    meta: ReturnType<typeof getMetricPresentation>;
    value: (typeof facts)[number];
    gap: number | null;
    good: boolean | null;
    rank?: (typeof facts)[number];
    median?: (typeof facts)[number];
    spread?: (typeof facts)[number];
  }>;

  if (cells.length === 0 || report.report_spec?.kind === 'answer_card') return null;

  // Single metric question: show the numbers that answer the question
  if (cells.length === 1) {
    const c = cells[0];
    const rankPos =
      c.rank?.rank_better ??
      (c.rank?.value !== null && c.rank?.value !== undefined ? Number(c.rank.value) : null);
    const denom = c.rank?.denominator ?? null;
    const medianVal =
      c.median && c.median.value !== null && c.median.value !== undefined
        ? formatMetricValue(c.median.value, c.meta)
        : null;

    interface KpiTile {
      id: string;
      label: string;
      value: string;
      caption?: string;
      subContent?: React.ReactNode;
      valueClassName?: string;
      captionClassName?: string;
    }

    const tiles: KpiTile[] = [];

    // 1. Value tile (always present when value fact exists)
    tiles.push({
      id: 'value',
      label: `${entity} · ${c.meta.shortLabel}`,
      value: formatMetricValue(c.value.value, c.meta),
      caption: 'Giá trị thực tế',
      valueClassName: 'text-text-primary'
    });

    // 2. Rank tile (only if peer_rank fact exists with a rank position)
    if (c.rank && (rankPos !== null || c.rank.value !== null)) {
      tiles.push({
        id: 'rank',
        label: 'Xếp hạng nhóm',
        value: rankPos ? (denom ? `#${rankPos}/${denom}` : `#${rankPos}`) : '—',
        subContent:
          rankPos && denom ? (
            <div className="mt-1 flex items-center gap-1.5" aria-label={`Hạng ${rankPos}/${denom}`}>
              <span className="flex flex-1 gap-0.5" aria-hidden="true">
                {Array.from({ length: denom }).map((_, k) => (
                  <i
                    key={k}
                    className={`h-1.5 flex-1 rounded-sm ${
                      k + 1 === rankPos ? 'bg-amber' : 'bg-surface-tertiary'
                    }`}
                  />
                ))}
              </span>
            </div>
          ) : null,
        caption: rankPos && denom ? undefined : 'Vị thế nhóm',
        valueClassName: 'text-text-primary'
      });
    }

    // 3. Peer Median tile (shown ONLY when peer_median fact exists and has non-null value)
    if (medianVal) {
      tiles.push({
        id: 'median',
        label: `Trung vị nhóm${denom ? ` (${denom} NH)` : ''}`,
        value: medianVal,
        caption: 'Mức chuẩn toàn nhóm',
        valueClassName: 'text-text-secondary'
      });
    }

    // 4. Gap tile (shown ONLY when gap exists, never show '—' with a claim)
    if (c.gap !== null && c.gap !== undefined) {
      const isNearZero = Math.abs(Number(c.gap)) < 0.005;
      const lowerBetter = c.meta.direction === 'lower_is_better';
      const isGood = isNearZero ? null : lowerBetter ? Number(c.gap) < 0 : Number(c.gap) > 0;

      tiles.push({
        id: 'gap',
        label: 'Chênh lệch',
        value: `${Number(c.gap) > 0 ? '+' : ''}${fmtPp(c.gap)}`,
        caption: isNearZero ? 'Ngang trung vị' : isGood ? '▲ Tốt hơn trung vị' : '▼ Kém hơn trung vị',
        valueClassName: isNearZero ? 'text-text-primary' : isGood ? 'text-text-success' : 'text-text-warning',
        captionClassName: isNearZero ? 'text-text-tertiary' : isGood ? 'text-text-success' : 'text-text-warning'
      });
    }

    // 5. Spread tile: When there is NO median fact but a 'spread' fact exists, show 'Chênh lệch cao – thấp'
    if (!medianVal && c.spread && c.spread.value !== null && c.spread.value !== undefined) {
      const spreadVal =
        c.meta.unit === '%' || c.spread.unit === 'điểm %' || c.spread.unit === 'pp'
          ? fmtPp(c.spread.value)
          : formatMetricValue(c.spread.value, c.meta);

      tiles.push({
        id: 'spread',
        label: 'Chênh lệch cao – thấp',
        value: spreadVal,
        caption: denom ? `Khoảng cách hạng 1 – ${denom}` : 'Biên độ phân hóa nhóm',
        valueClassName: 'text-text-primary'
      });
    }

    const gridColsClass =
      tiles.length === 1
        ? 'grid-cols-1'
        : tiles.length === 2
          ? 'grid-cols-2'
          : tiles.length === 3
            ? 'grid-cols-1 sm:grid-cols-3'
            : 'grid-cols-2 sm:grid-cols-4';

    const getBorderClass = (i: number) => {
      if (tiles.length === 3) {
        return i > 0 ? 'border-t sm:border-t-0 sm:border-l' : '';
      }
      if (tiles.length === 2) {
        return i > 0 ? 'border-l' : '';
      }
      if (tiles.length === 1) {
        return '';
      }
      return `${i % 2 === 1 ? 'border-l' : ''} ${i >= 2 ? 'border-t sm:border-t-0' : ''} ${
        i > 0 ? 'sm:border-l' : ''
      }`;
    };

    return (
      <div
        className={`mt-5 grid ${gridColsClass} overflow-hidden rounded-xl border border-border-subtle bg-surface-primary`}
        role="group"
        aria-label={`Chỉ số chính của ${entity}`}
      >
        {tiles.map((tile, i) => (
          <div key={tile.id} className={`p-4 ${getBorderClass(i)} border-border-subtle`}>
            <p className="m-0 text-xs font-medium text-text-tertiary">{tile.label}</p>
            <p className={`mt-1.5 mb-1 text-[26px] font-semibold leading-none tabular-nums ${tile.valueClassName || 'text-text-primary'}`}>
              {tile.value}
            </p>
            {tile.subContent ? (
              tile.subContent
            ) : tile.caption ? (
              <p className={`m-0 text-xs tabular-nums ${tile.captionClassName || 'text-text-tertiary'}`}>
                {tile.caption}
              </p>
            ) : null}
          </div>
        ))}
      </div>
    );
  }

  // Multi-metric question (2 to 4 metrics)
  const displayCells = cells.slice(0, 4);

  return (
    <div
      className="mt-5 grid grid-cols-2 overflow-hidden rounded-xl border border-border-subtle sm:grid-cols-4 bg-surface-primary"
      role="group"
      aria-label={`Chỉ số chính của ${entity}`}
    >
      {displayCells.map((c, i) => {
        const rankPos = c.rank?.rank_better ?? (c.rank?.value !== null && c.rank?.value !== undefined ? Number(c.rank.value) : null);
        const denom = c.rank?.denominator ?? null;
        const medianVal = c.median && c.median.value !== null ? formatMetricValue(c.median.value, c.meta) : null;

        return (
          <div
            key={c.metricId}
            className={`p-4 ${i % 2 === 1 ? 'border-l' : ''} ${i >= 2 ? 'border-t sm:border-t-0' : ''} ${
              i > 0 ? 'sm:border-l' : ''
            } border-border-subtle`}
          >
            <p className="m-0 text-xs font-medium text-text-tertiary">{c.meta.shortLabel}</p>
            <p className="mt-1.5 mb-1 text-[26px] font-semibold leading-none tabular-nums text-text-primary">
              {formatMetricValue(c.value.value, c.meta)}
            </p>
            {c.gap !== null ? (
              <p
                className={`m-0 text-xs tabular-nums ${
                  c.good === null ? 'text-text-tertiary' : c.good ? 'text-text-success' : 'text-text-warning'
                }`}
              >
                {c.good === null ? '— ngang trung vị' : `${c.good ? '▲' : '▼'} ${Number(c.gap) > 0 ? '+' : ''}${fmtPp(c.gap)}`}
                {medianVal ? ` (TV: ${medianVal})` : ' so với trung vị'}
              </p>
            ) : (
              <p className="m-0 text-xs text-text-tertiary">&nbsp;</p>
            )}
            {rankPos && denom ? (
              <div className="mt-2.5 flex items-center gap-2" aria-label={`Hạng ${rankPos}/${denom}`}>
                <span className="flex flex-1 gap-0.5" aria-hidden="true">
                  {Array.from({ length: denom }).map((_, k) => (
                    <i key={k} className={`h-1.5 flex-1 rounded-sm ${k + 1 === rankPos ? 'bg-amber' : 'bg-surface-tertiary'}`} />
                  ))}
                </span>
                <span className="text-[11px] tabular-nums text-text-secondary">
                  #{rankPos}/{denom}
                </span>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
};
