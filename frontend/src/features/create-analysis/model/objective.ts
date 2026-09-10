import type { AnalysisCapabilities } from '../../../entities/capability/model/types';
import type { AnalysisFormValues } from '../schema';

export function getScopeSignature(values: Pick<AnalysisFormValues, 'analysisTargetIds' | 'periodIds' | 'metricIds'>) {
  return JSON.stringify({
    analysisTargetIds: [...values.analysisTargetIds].sort(),
    periodIds: [...values.periodIds].sort(),
    metricIds: [...values.metricIds].sort()
  });
}

function joinVietnamese(items: string[]) {
  if (items.length <= 1) return items[0] ?? '';
  if (items.length === 2) return items.join(' và ');
  return `${items.slice(0, -1).join(', ')} và ${items.at(-1)}`;
}

function formatPeriods(values: AnalysisFormValues, capabilities: AnalysisCapabilities) {
  const selected = capabilities.periods
    .filter((period) => values.periodIds.includes(period.id))
    .sort((a, b) => a.quarter - b.quarter);

  if (selected.length === 4 && selected.every((period) => period.year === 2024)) {
    return 'Q1–Q4/2024';
  }

  return joinVietnamese(selected.map((period) => period.label));
}

export function generateSuggestedObjective(values: AnalysisFormValues, capabilities: AnalysisCapabilities) {
  const targets = capabilities.entities
    .filter((entity) => values.analysisTargetIds.includes(entity.id))
    .map((entity) => entity.ticker);
  const metrics = capabilities.metrics
    .filter((metric) => values.metricIds.includes(metric.id))
    .map((metric) => metric.acronym);

  return `Phân tích ${joinVietnamese(metrics)} của ${joinVietnamese(targets)} trong ${formatPeriods(values, capabilities)}, đồng thời đối chiếu với ${capabilities.peerUniverse.label.toLowerCase()} đã được xác thực.`;
}

export function hasPossibleObjectiveMismatch(objective: string) {
  const normalized = objective.toLowerCase();
  const unsupportedMetricMention = ['nim', 'casa', 'cir', 'ldr'].some((term) => normalized.includes(term));
  const unsupportedPeriodMention = ['2023', '2025', '2026'].some((period) => normalized.includes(period));
  return unsupportedMetricMention || unsupportedPeriodMention;
}
