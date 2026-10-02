import { describe, expect, it } from 'vitest';
import { formatCapabilitiesPeriods } from '../src/features/analysis-session/useTraceStream';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';
import type { AnalysisCapabilities } from '../src/entities/capability/model/types';

const ALL = ['bank.npl_g35', 'bank.llr_coverage', 'bank.roa', 'bank.roe'];

function caps(periodIds: string[], withMetrics: string[]): AnalysisCapabilities {
  return {
    ...mockCapabilities,
    periods: periodIds.map((id) => {
      const [year, q] = id.split('_Q');
      return { id, label: id, year: Number(year), quarter: Number(q) };
    }) as AnalysisCapabilities['periods'],
    coverage: periodIds.map((period_id) => ({
      entity_id: 'AAA',
      period_id,
      metrics: withMetrics.includes(period_id) ? ALL : []
    }))
  };
}

describe('formatCapabilitiesPeriods', () => {
  it('spans the first to the last quarter that carries metrics across years', () => {
    const analytical = ['2024_Q1', '2024_Q4', '2025_Q3', '2026_Q2'];
    expect(formatCapabilitiesPeriods(caps(['2023_Q3', '2023_Q4', ...analytical], analytical))).toBe('Q1/2024–Q2/2026');
  });

  it('keeps the single-year form when every analytical quarter is in one year', () => {
    const analytical = ['2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4'];
    expect(formatCapabilitiesPeriods(caps(['2023_Q4', ...analytical], analytical))).toBe('Q1–Q4/2024');
  });
});
