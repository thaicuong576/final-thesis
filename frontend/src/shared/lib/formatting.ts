import type { Period } from '../../entities/capability/model/types';

export function formatPeriodLabel(period: Period) {
  return `Q${period.quarter}/${period.year}`;
}

function joinVietnamese(items: string[]) {
  if (items.length <= 1) return items[0] ?? '';
  if (items.length === 2) return items.join(' và ');
  return `${items.slice(0, -1).join(', ')} và ${items.at(-1)}`;
}

export function formatPeriodCollection(periods: Period[]) {
  const groups = new Map<number, number[]>();
  for (const period of periods) {
    const quarters = groups.get(period.year) ?? [];
    quarters.push(period.quarter);
    groups.set(period.year, quarters);
  }

  return [...groups.entries()]
    .sort(([yearA], [yearB]) => yearA - yearB)
    .map(([year, quarters]) => {
      const sortedQuarters = [...new Set(quarters)].sort((quarterA, quarterB) => quarterA - quarterB);
      if (sortedQuarters.length > 1 && sortedQuarters.every((quarter, index) => index === 0 || quarter === sortedQuarters[index - 1] + 1)) {
        return `Q${sortedQuarters[0]}–Q${sortedQuarters.at(-1)}/${year}`;
      }
      return `${joinVietnamese(sortedQuarters.map((quarter) => `Q${quarter}`))}/${year}`;
    })
    .join(' · ');
}

export function formatCapabilityTimestamp(timestamp: string) {
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Ho_Chi_Minh'
  }).format(new Date(timestamp));
}

export function formatGoldVersion(version: string) {
  return `Gold v${version}`;
}

/**
 * Gracefully formats financial metrics with fallback to 'N/A' when values are null, undefined, or invalid.
 */
export function formatMetric(
  value: number | string | null | undefined,
  digits = 1,
  suffix = '%'
): string {
  if (value === null || value === undefined || value === '' || isNaN(Number(value))) {
    return 'N/A';
  }
  return `${Number(value).toFixed(digits)}${suffix}`;
}
