import type { MetricPresentation } from './types';
import { fmtPct, fmtPp, fmtTimes } from '@/shared/lib/formatting';
import { DEFAULT_METRICS } from '@/shared/lib/defaultMetrics';

export { DEFAULT_METRICS };

export function getMetricPresentation(
  metricId: string,
  providedList?: MetricPresentation[]
): MetricPresentation {
  if (providedList && providedList.length > 0) {
    const found = providedList.find((m) => m.id === metricId);
    if (found) return found;
  }
  if (DEFAULT_METRICS[metricId]) {
    return DEFAULT_METRICS[metricId];
  }
  const clean = metricId.replace(/^(bank|derived|macro|sector)\./, '');
  return {
    id: metricId,
    acronym: clean.toUpperCase(),
    label: clean,
    shortLabel: clean,
    unit: '%',
    direction: 'higher_is_better',
    decimals: 1,
    group: 'general',
    groupLabel: 'Chung'
  };
}

export function formatMetricValue(
  value: number | string | null | undefined,
  metric: MetricPresentation
): string {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
    return '—';
  }
  const num = Number(value);
  if (metric.unit === '%') {
    return fmtPct(num, metric.decimals);
  }
  if (metric.unit === 'pp') {
    return fmtPp(num, metric.decimals);
  }
  if (metric.unit === 'lần' || metric.unit === 'times') {
    return fmtTimes(num, metric.decimals);
  }
  const formatted = new Intl.NumberFormat('vi-VN', {
    minimumFractionDigits: metric.decimals,
    maximumFractionDigits: metric.decimals
  }).format(num);
  return metric.unit ? `${formatted} ${metric.unit}` : formatted;
}
