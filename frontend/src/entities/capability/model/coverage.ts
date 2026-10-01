import type { AnalysisCapabilities, CoverageItem } from './types';

const PERIOD_RE = /^(\d{4})[_ -]?[Qq](\d)$/;

export function periodOrder(a: string, b: string): number {
  const ma = a.match(PERIOD_RE);
  const mb = b.match(PERIOD_RE);
  if (ma && mb) return Number(ma[1]) - Number(mb[1]) || Number(ma[2]) - Number(mb[2]);
  return a.localeCompare(b);
}

export function formatQuarter(periodId: string): string {
  const m = periodId.match(PERIOD_RE);
  return m ? `Q${m[2]}/${m[1]}` : periodId;
}

/**
 * Periods that carry at least one analytical metric for some bank. Prior-year periods that
 * only hold inputs for averages (e.g. 2023 balances behind 2024 ROA) are not offered to users.
 * Falls back to every catalog period when the API does not publish coverage.
 */
export function analyticalPeriodIds(caps: Pick<AnalysisCapabilities, 'periods' | 'coverage'>): string[] {
  const coverage: CoverageItem[] = caps.coverage ?? [];
  const withData = new Set(coverage.filter((c) => c.metrics?.length).map((c) => c.period_id));
  const ids = withData.size ? Array.from(withData) : (caps.periods ?? []).map((p) => p.id);
  return ids.sort(periodOrder);
}
