import type React from 'react';
import type { ChartType } from '../model/types';
import type { ChartProps } from './types';
import { KpiStrip } from './KpiStrip';
import { RankedBar } from './RankedBar';
import { LineTrend } from './LineTrend';
import { SmallMultiples } from './SmallMultiples';
import { Scatter } from './Scatter';
import { RankHeatmap } from './RankHeatmap';
import { GroupedBar } from './GroupedBar';
import { ComparisonTable } from './ComparisonTable';

export * from './types';
export * from './KpiStrip';
export * from './RankedBar';
export * from './LineTrend';
export * from './SmallMultiples';
export * from './Scatter';
export * from './RankHeatmap';
export * from './GroupedBar';
export * from './ComparisonTable';
export * from './DataTable';

export const CHARTS: Record<ChartType, React.ComponentType<ChartProps>> = {
  kpi_strip: KpiStrip,
  ranked_bar: RankedBar,
  line_trend: LineTrend,
  small_multiples: SmallMultiples,
  scatter: Scatter,
  rank_heatmap: RankHeatmap,
  grouped_bar: GroupedBar,
  comparison_table: ComparisonTable
};
