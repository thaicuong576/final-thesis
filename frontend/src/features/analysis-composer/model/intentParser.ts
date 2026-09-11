import type { AnalysisCapabilities, Entity, Metric, Period } from '@/entities/capability/model/types';
import type {
  AnalyticalCapabilityItem,
  ParseResult,
  ParsedScope,
  ScopeMismatch
} from './types';

/**
 * Client-side intent parser for Screen 1 prototype.
 * NOTE: This is a client-side preview/mock implementation of the query-adaptive
 * request interpretation. In production, this will be replaced by the backend
 * planning endpoint that returns a validated AnalysisPlan.
 *
 * All entities, periods, metrics, and universe references are derived from the
 * injected AnalysisCapabilities contract.
 */
export function parseAnalysisQuestion(
  question: string,
  capabilities: AnalysisCapabilities
): ParseResult {
  const normalized = question.toLowerCase();

  // 1. Check for unsupported requests against capability boundaries
  const mismatch = detectScopeMismatch(normalized, capabilities);
  if (mismatch.isMismatch) {
    const emptyScope: ParsedScope = {
      entities: [],
      periods: [],
      metrics: [],
      topicLabels: [],
      scopeSignature: '',
      analysisPlan: { selectedCapabilities: [] }
    };
    return {
      rawQuestion: question,
      scope: emptyScope,
      mismatch
    };
  }

  // 2. Extract supported entities from capabilities
  const matchedEntities = capabilities.entities.filter((entity) => {
    const ticker = entity.ticker.toLowerCase();
    const name = entity.name.toLowerCase();
    return normalized.includes(ticker) || normalized.includes(name);
  });

  const finalEntities: Entity[] =
    matchedEntities.length > 0 ? matchedEntities : capabilities.entities;

  // 3. Extract supported periods from capabilities
  const matchedPeriods = capabilities.periods.filter((period) => {
    const qStr = `q${period.quarter}`;
    const quyStr = `quý ${period.quarter}`;
    return normalized.includes(qStr) || normalized.includes(quyStr);
  });

  const finalPeriods: Period[] =
    matchedPeriods.length > 0 ? matchedPeriods : capabilities.periods;

  // 4. Extract supported metrics and topic cues
  const matchedMetrics: Metric[] = [];
  const topicLabels: string[] = [];

  for (const metric of capabilities.metrics) {
    const acr = metric.acronym.toLowerCase();
    const lbl = metric.label.toLowerCase();
    if (normalized.includes(acr) || normalized.includes(lbl)) {
      if (!matchedMetrics.some((m) => m.id === metric.id)) {
        matchedMetrics.push(metric);
      }
    }
  }

  const hasSpecificMetricMention = matchedMetrics.length > 0;

  if (
    normalized.includes('tài sản') ||
    normalized.includes('nợ') ||
    normalized.includes('npl') ||
    normalized.includes('coverage') ||
    normalized.includes('bao phủ')
  ) {
    topicLabels.push('Chất lượng tài sản');
    if (!hasSpecificMetricMention) {
      capabilities.metrics
        .filter((m) => m.topicId === 'asset-quality')
        .forEach((m) => {
          if (!matchedMetrics.some((existing) => existing.id === m.id)) {
            matchedMetrics.push(m);
          }
        });
    }
  }

  if (
    normalized.includes('sinh lời') ||
    normalized.includes('hiệu quả') ||
    normalized.includes('roa') ||
    normalized.includes('roe')
  ) {
    topicLabels.push('Khả năng sinh lời');
    if (!hasSpecificMetricMention) {
      capabilities.metrics
        .filter((m) => m.topicId === 'profitability')
        .forEach((m) => {
          if (!matchedMetrics.some((existing) => existing.id === m.id)) {
            matchedMetrics.push(m);
          }
        });
    }
  }

  const finalMetrics =
    matchedMetrics.length > 0 ? matchedMetrics : capabilities.metrics;

  if (topicLabels.length === 0) {
    topicLabels.push('Chất lượng tài sản & Khả năng sinh lời');
  }

  // 5. Query-Adaptive Capability Selection (AnalysisPlan)
  // Determine which analytical capabilities are selected for this query
  const selectedCapabilities: AnalyticalCapabilityItem[] = [];

  // A. Company Analysis: Always selected when evaluating entity/entities
  selectedCapabilities.push({
    id: 'company',
    label: 'Phân tích doanh nghiệp',
    description: `Phân tích dữ liệu tài chính của ${finalEntities.map((e) => e.ticker).join(', ')}`,
    selected: true
  });

  // B. Peer / Reference Universe Analysis: Selected when comparison, ranking,
  // or multiple entities are requested
  const isPeerComparisonRequested =
    normalized.includes('so sánh') ||
    normalized.includes('nhóm so sánh') ||
    normalized.includes('nhóm tham chiếu') ||
    normalized.includes('đối sánh') ||
    normalized.includes('benchmark') ||
    normalized.includes('ngành') ||
    normalized.includes('toàn hệ thống') ||
    normalized.includes('dẫn đầu') ||
    normalized.includes('tốt hơn') ||
    normalized.includes('kém') ||
    matchedEntities.length > 1;

  if (isPeerComparisonRequested && capabilities.peerUniverse) {
    selectedCapabilities.push({
      id: 'peer',
      label: 'Nhóm tham chiếu',
      description: `Đối sánh cùng kỳ với ${capabilities.peerUniverse.label}`,
      selected: true
    });
  }

  // C. Macro Context Analysis: Selected when macroeconomic keywords are present
  // and macro capability is available
  const isMacroRequested =
    normalized.includes('vĩ mô') ||
    normalized.includes('lãi suất') ||
    normalized.includes('chính sách tiền tệ') ||
    normalized.includes('tín dụng') ||
    normalized.includes('ngân hàng nhà nước') ||
    normalized.includes('sbv') ||
    normalized.includes('lạm phát');

  if (isMacroRequested && capabilities.macro.status !== 'UNAVAILABLE') {
    selectedCapabilities.push({
      id: 'macro',
      label: 'Bối cảnh vĩ mô',
      description: 'Tích hợp diễn biến chính sách tiền tệ và tăng trưởng tín dụng',
      selected: true
    });
  }

  // 6. Build concise scope signature: e.g. "TCB · Q1–Q4/2024 · ROE"
  const entitySig = finalEntities.map((e) => e.ticker).join(' · ');
  const periodSig = formatPeriodsSignature(finalPeriods);
  const metricSig = finalMetrics.map((m) => m.acronym).join(' · ');
  const scopeSignature = [entitySig, periodSig, metricSig].filter(Boolean).join(' · ');

  const scope: ParsedScope = {
    entities: finalEntities,
    periods: finalPeriods,
    metrics: finalMetrics,
    topicLabels,
    scopeSignature,
    analysisPlan: {
      selectedCapabilities
    },
    referenceUniverseLabel: capabilities.peerUniverse?.label
  };

  return {
    rawQuestion: question,
    scope,
    mismatch
  };
}

function formatPeriodsSignature(periods: Period[]): string {
  if (periods.length === 0) return '';
  if (periods.length === 4) return 'Q1–Q4/2024';
  return periods.map((p) => `Q${p.quarter}/${p.year}`).join(', ');
}

function detectScopeMismatch(
  normalized: string,
  capabilities: AnalysisCapabilities
): ScopeMismatch {
  const unsupportedEntities: string[] = [];
  const unsupportedPeriods: string[] = [];
  const unsupportedMetrics: string[] = [];

  // Out-of-scope bank cues for prototype testing
  const knownOtherBanks = ['bidv', 'ctg', 'stb', 'hdb', 'shb', 'tpbank', 'tpb', 'lpbank', 'lpb'];
  for (const b of knownOtherBanks) {
    if (normalized.includes(b)) {
      unsupportedEntities.push(b.toUpperCase());
    }
  }

  // Out-of-scope years for prototype testing
  const pastYears = ['2023', '2022', '2021', '2020'];
  for (const yr of pastYears) {
    if (normalized.includes(yr)) {
      unsupportedPeriods.push(yr);
    }
  }

  // Out-of-scope metrics
  const knownOtherMetrics: { key: string; label: string }[] = [
    { key: 'eps', label: 'EPS' },
    { key: 'p/e', label: 'P/E' },
    { key: 'pe ', label: 'P/E' },
    { key: 'casa', label: 'CASA' },
    { key: 'nim', label: 'NIM' },
    { key: 'cir', label: 'CIR' },
    { key: 'car', label: 'CAR' }
  ];
  for (const m of knownOtherMetrics) {
    if (normalized.includes(m.key)) {
      if (!unsupportedMetrics.includes(m.label)) {
        unsupportedMetrics.push(m.label);
      }
    }
  }

  const isMismatch =
    unsupportedEntities.length > 0 ||
    unsupportedPeriods.length > 0 ||
    unsupportedMetrics.length > 0;

  const availableCapabilitiesSummary = {
    periods: 'Q1–Q4/2024',
    metrics: capabilities.metrics.map((m) => m.acronym).join(', '),
    entities: capabilities.entities.map((e) => e.ticker).join(', ')
  };

  let reason = '';
  if (isMismatch) {
    const parts: string[] = [];
    if (unsupportedMetrics.length > 0) {
      parts.push(`chỉ số ${unsupportedMetrics.join(', ')}`);
    }
    if (unsupportedPeriods.length > 0) {
      parts.push(`chu kỳ năm ${unsupportedPeriods.join(', ')}`);
    }
    if (unsupportedEntities.length > 0) {
      parts.push(`ngân hàng ${unsupportedEntities.join(', ')}`);
    }
    reason = `Bộ dữ liệu hiện tại không có ${parts.join(' và ')}.`;
  }

  return {
    isMismatch,
    reason,
    unsupportedEntities: unsupportedEntities.length > 0 ? unsupportedEntities : undefined,
    unsupportedPeriods: unsupportedPeriods.length > 0 ? unsupportedPeriods : undefined,
    unsupportedMetrics: unsupportedMetrics.length > 0 ? unsupportedMetrics : undefined,
    availableCapabilitiesSummary
  };
}
