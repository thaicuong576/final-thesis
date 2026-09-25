import type { AnalysisCapabilities } from '../../../entities/capability/model/types';
import type { AnalysisFormValues } from '../schema';
import { formatPeriodCollection } from '../../../shared/lib/formatting';

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

export function generateSuggestedObjective(values: AnalysisFormValues, capabilities: AnalysisCapabilities) {
  const targets = capabilities.entities
    .filter((entity) => values.analysisTargetIds.includes(entity.id))
    .map((entity) => entity.ticker);
  const metrics = capabilities.metrics
    .filter((metric) => values.metricIds.includes(metric.id))
    .map((metric) => metric.acronym);
  const periods = capabilities.periods.filter((period) => values.periodIds.includes(period.id));

  return `Phân tích ${joinVietnamese(metrics)} của ${joinVietnamese(targets)} trong ${formatPeriodCollection(periods)}${capabilities.peerUniverse?.label ? `; nhóm tham chiếu trong catalog: ${capabilities.peerUniverse.label.toLowerCase()}` : ''}.`;
}

function normalize(text: string) {
  return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function mentions(text: string, term: string) {
  const normalizedTerm = normalize(term);
  if (!normalizedTerm) return false;
  if (normalizedTerm.length <= 3 && /^[a-z0-9]+$/.test(normalizedTerm)) {
    return new RegExp(`\\b${normalizedTerm}\\b`, 'i').test(text);
  }
  return text.includes(normalizedTerm);
}

export function hasPossibleObjectiveMismatch(
  objective: string,
  capabilities: AnalysisCapabilities,
  values: Pick<AnalysisFormValues, 'analysisTargetIds' | 'periodIds' | 'metricIds'>
) {
  const normalizedObjective = normalize(objective);
  const selectedTargetIds = new Set(values.analysisTargetIds);
  const selectedPeriodIds = new Set(values.periodIds);
  const selectedMetricIds = new Set(values.metricIds);

  const mentionsUnselectedEntity = capabilities.entities.some((entity) => {
    const mentioned = mentions(normalizedObjective, entity.ticker) || mentions(normalizedObjective, entity.name);
    return mentioned && !selectedTargetIds.has(entity.id);
  });
  const mentionsUnselectedMetric = capabilities.metrics.some((metric) => {
    const mentioned = mentions(normalizedObjective, metric.acronym) || mentions(normalizedObjective, metric.label);
    return mentioned && !selectedMetricIds.has(metric.id);
  });
  const mentionsUnselectedPeriod = capabilities.periods.some((period) => {
    const periodLabel = `q${period.quarter}/${period.year}`;
    return normalizedObjective.includes(periodLabel) && !selectedPeriodIds.has(period.id);
  });
  const selectedYears = new Set(capabilities.periods.filter((period) => selectedPeriodIds.has(period.id)).map((period) => period.year));
  const mentionedYears = [...normalizedObjective.matchAll(/\b(?:19|20)\d{2}\b/g)].map((match) => Number(match[0]));
  const mentionsOutOfScopeYear = mentionedYears.some((year) => !selectedYears.has(year));

  return mentionsUnselectedEntity || mentionsUnselectedMetric || mentionsUnselectedPeriod || mentionsOutOfScopeYear;
}
