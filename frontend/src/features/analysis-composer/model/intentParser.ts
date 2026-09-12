import type { AnalysisCapabilities, Entity, Metric, Period } from '@/entities/capability/model/types';
import type {
  AnalyticalCapabilityId,
  AnalyticalCapabilityItem,
  ParseResult,
  ParsedScope,
  ScopeMismatch
} from './types';

/**
 * Formats periods into a human-readable signature dynamically grouping by year.
 * e.g. "Q1–Q4/2024" if all 4 quarters, or "Q1–Q2/2024", or "Q1/2024, Q3/2024".
 * No hardcoded years or "length === 4" assumptions.
 */
export function formatPeriodsSignature(periods: Period[]): string {
  if (!periods || periods.length === 0) return '';

  const byYear = new Map<number, number[]>();
  for (const p of periods) {
    const quarters = byYear.get(p.year) || [];
    if (!quarters.includes(p.quarter)) {
      quarters.push(p.quarter);
    }
    byYear.set(p.year, quarters);
  }

  const parts: string[] = [];
  for (const [year, quarters] of byYear.entries()) {
    quarters.sort((a, b) => a - b);
    if (quarters.length === 4 && quarters[0] === 1 && quarters[3] === 4) {
      parts.push(`Q1–Q4/${year}`);
    } else if (
      quarters.length > 1 &&
      quarters[quarters.length - 1] - quarters[0] === quarters.length - 1
    ) {
      parts.push(`Q${quarters[0]}–Q${quarters[quarters.length - 1]}/${year}`);
    } else {
      parts.push(quarters.map((q) => `Q${q}/${year}`).join(', '));
    }
  }

  return parts.join(' · ');
}

export interface PlanCapabilitiesParams {
  entities: Entity[];
  capabilities: AnalysisCapabilities;
  rawQuestion?: string;
  forcePeerComparison?: boolean;
  preserveCapabilities?: AnalyticalCapabilityId[];
}

/**
 * Plans analytical capabilities dynamically based on user intent and dataset capabilities.
 * The user adjusts business/data scope; the planner decides which capabilities to run.
 */
export function planAnalyticalCapabilities({
  entities,
  capabilities,
  rawQuestion = '',
  forcePeerComparison = false,
  preserveCapabilities = []
}: PlanCapabilitiesParams): AnalyticalCapabilityItem[] {
  const normalized = rawQuestion.toLowerCase();
  const selectedCapabilities: AnalyticalCapabilityItem[] = [];

  // 1. Company Analysis: Selected IF AND ONLY IF specific target entities are included
  if (entities.length > 0) {
    selectedCapabilities.push({
      id: 'company',
      label: 'Phân tích doanh nghiệp',
      description: `Phân tích dữ liệu tài chính của ${entities.map((e) => e.ticker).join(', ')}`,
      selected: true
    });
  }

  // 2. Peer / Reference Universe Analysis:
  // Selected when explicit comparison is requested, multiple entities exist,
  // or a sector-level analysis is requested without single-company focus.
  const isPeerComparisonRequested =
    preserveCapabilities.includes('peer') ||
    normalized.includes('so sánh') ||
    normalized.includes('nhóm so sánh') ||
    normalized.includes('nhóm tham chiếu') ||
    normalized.includes('đối sánh') ||
    normalized.includes('benchmark') ||
    normalized.includes('ngành') ||
    normalized.includes('toàn hệ thống') ||
    normalized.includes('toàn ngành') ||
    normalized.includes('trung vị') ||
    normalized.includes('dẫn đầu') ||
    normalized.includes('tốt hơn') ||
    normalized.includes('kém') ||
    normalized.includes('xếp hạng');

  const hasMacroOnlyKeywords =
    (normalized.includes('vĩ mô') ||
      normalized.includes('lãi suất') ||
      normalized.includes('chính sách tiền tệ')) &&
    !isPeerComparisonRequested;

  const shouldActivatePeer =
    Boolean(capabilities.peerUniverse) &&
    (forcePeerComparison ||
      isPeerComparisonRequested ||
      entities.length > 1 ||
      (entities.length === 0 && !hasMacroOnlyKeywords));

  if (shouldActivatePeer && capabilities.peerUniverse) {
    selectedCapabilities.push({
      id: 'peer',
      label: 'Nhóm tham chiếu',
      description: `Đối sánh cùng kỳ với ${capabilities.peerUniverse.label}`,
      selected: true
    });
  }

  // 3. Macro Context Analysis: Selected when macroeconomic keywords are present
  // and macro capability is available in dataset capabilities.
  const isMacroRequested =
    preserveCapabilities.includes('macro') ||
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

  return selectedCapabilities;
}

/**
 * Client-side intent parser for Screen 1 prototype (heuristic / mock implementation).
 *
 * NOTE: This is an explicit frontend prototype/mock heuristic for developer preview
 * and UI validation. The authoritative production AnalysisPlan will come from the backend
 * planner according to the data contract. It is intentionally kept simple and not a general NLP engine.
 *
 * All entities, periods, metrics, and universe references are derived dynamically
 * from the injected AnalysisCapabilities contract.
 */
export function parseAnalysisQuestion(
  rawQuestion: string,
  capabilities: AnalysisCapabilities
): ParseResult {
  const question = rawQuestion;
  const normalized = rawQuestion.toLowerCase();

  // 1. Check for unsupported requests dynamically against capability boundaries
  const mismatch = detectScopeMismatch(question, normalized, capabilities);
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

  // Determine if question is Peer-only or Macro-only (no specific entity named)
  const isPeerCues =
    normalized.includes('so sánh') ||
    normalized.includes('nhóm so sánh') ||
    normalized.includes('nhóm tham chiếu') ||
    normalized.includes('đối sánh') ||
    normalized.includes('toàn ngành') ||
    normalized.includes('toàn hệ thống') ||
    normalized.includes('ngành');

  const isMacroCues =
    normalized.includes('vĩ mô') ||
    normalized.includes('lãi suất') ||
    normalized.includes('chính sách tiền tệ') ||
    normalized.includes('tín dụng') ||
    normalized.includes('ngân hàng nhà nước') ||
    normalized.includes('sbv') ||
    normalized.includes('lạm phát');

  let finalEntities: Entity[] = [];
  if (matchedEntities.length > 0) {
    finalEntities = matchedEntities;
  } else if (!isPeerCues && !isMacroCues) {
    // High-level or general question with no entity specified: default to all dataset entities
    finalEntities = capabilities.entities;
  }

  // 3. Extract supported periods from capabilities dynamically
  // Capability-driven period resolution: resolve explicit years and quarters without hardcoded years
  const supportedYears = new Set(capabilities.periods.map((p) => p.year));
  const yearMatches = rawQuestion.match(/\b(19\d\d|20\d\d)\b/g);
  const explicitYears = yearMatches
    ? [...new Set(yearMatches.map((y) => parseInt(y, 10)).filter((y) => supportedYears.has(y)))]
    : [];

  const explicitQuarters: number[] = [];
  for (let q = 1; q <= 4; q++) {
    const qRegex = new RegExp(`(\\bq${q}\\b|quý\\s*${q}\\b)`, 'i');
    if (qRegex.test(rawQuestion)) {
      explicitQuarters.push(q);
    }
  }

  let matchedPeriods: Period[] = [];
  if (explicitYears.length > 0 && explicitQuarters.length > 0) {
    // Both explicit year and quarter specified (e.g. "ROE TCB Q4/2024")
    matchedPeriods = capabilities.periods.filter(
      (p) => explicitYears.includes(p.year) && explicitQuarters.includes(p.quarter)
    );
  } else if (explicitYears.length > 0) {
    // Explicit year specified without specific quarter (e.g. "ROE của TCB trong năm 2024")
    matchedPeriods = capabilities.periods.filter((p) => explicitYears.includes(p.year));
  } else if (explicitQuarters.length > 0) {
    // Explicit quarter specified without specific year
    matchedPeriods = capabilities.periods.filter((p) => explicitQuarters.includes(p.quarter));
  }

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

  // 5. Query-Adaptive Capability Selection (AnalysisPlan)
  const selectedCapabilities = planAnalyticalCapabilities({
    entities: finalEntities,
    capabilities,
    rawQuestion: question
  });

  const isMacroOnly =
    selectedCapabilities.length === 1 && selectedCapabilities[0].id === 'macro';

  let finalMetrics: Metric[] = [];
  if (isMacroOnly) {
    // If request is Macro-only, do not attach company metrics (NPL, Coverage, ROA, ROE).
    // The current capability contract has no explicit macro metric catalog,
    // so company metric scope is represented as empty / not applicable.
    finalMetrics = [];
    if (topicLabels.length === 0) {
      topicLabels.push('Bối cảnh vĩ mô');
    }
  } else {
    finalMetrics = matchedMetrics.length > 0 ? matchedMetrics : capabilities.metrics;
    if (topicLabels.length === 0) {
      topicLabels.push('Chất lượng tài sản & Khả năng sinh lời');
    }
  }

  // 6. Build concise scope signature dynamically
  const entitySig =
    finalEntities.length > 0
      ? finalEntities.map((e) => e.ticker).join(' · ')
      : selectedCapabilities.some((c) => c.id === 'peer')
      ? capabilities.peerUniverse?.label || 'Toàn ngành'
      : isMacroOnly
      ? 'Toàn hệ thống'
      : '';

  const periodSig = formatPeriodsSignature(finalPeriods);
  const metricSig = finalMetrics.map((m) => m.acronym).join(' · ');
  const scopeSignature = [entitySig, periodSig, metricSig].filter(Boolean).join(' · ');

  const scope: ParsedScope = {
    rawQuestion: question,
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

/**
 * Dynamically detects mismatch between user question and active AnalysisCapabilities.
 * Does NOT rely on hardcoded bank lists or past years.
 */
function detectScopeMismatch(
  rawQuestion: string,
  normalized: string,
  capabilities: AnalysisCapabilities
): ScopeMismatch {
  const unsupportedEntities: string[] = [];
  const unsupportedPeriods: string[] = [];
  const unsupportedMetrics: string[] = [];

  const supportedTickers = new Set(capabilities.entities.map((e) => e.ticker.toUpperCase()));
  const supportedNames = capabilities.entities.map((e) => e.name.toLowerCase());
  const supportedYears = new Set(capabilities.periods.map((p) => p.year));
  const supportedMetricAcronyms = new Set(capabilities.metrics.map((m) => m.acronym.toUpperCase()));

  // 1. Dynamic 4-digit year detection (e.g. 2025, 2023, 2022)
  const yearMatches = rawQuestion.match(/\b(19\d\d|20\d\d)\b/g);
  if (yearMatches) {
    for (const yrStr of yearMatches) {
      const yr = parseInt(yrStr, 10);
      if (!supportedYears.has(yr) && !unsupportedPeriods.includes(yrStr)) {
        unsupportedPeriods.push(yrStr);
      }
    }
  }

  // 2. Dynamic financial metric extraction & non-membership detection
  const candidateMetricAcronyms = [
    'EPS',
    'PE',
    'P/E',
    'PB',
    'P/B',
    'NIM',
    'CASA',
    'CIR',
    'CAR',
    'LDR',
    'COF',
    'YOEA',
    'NOI',
    'EBIT',
    'EBITDA'
  ];

  for (const acr of candidateMetricAcronyms) {
    const escaped = acr.replace('/', '\\/');
    const reg = new RegExp(`(^|[^a-zA-Z0-9/])${escaped}([^a-zA-Z0-9/]|$)`, 'i');
    if (reg.test(rawQuestion)) {
      const isSupported =
        supportedMetricAcronyms.has(acr.toUpperCase()) ||
        capabilities.metrics.some((m) => m.acronym.toUpperCase() === acr.toUpperCase());
      if (!isSupported) {
        const displayLabel = acr === 'PE' ? 'P/E' : acr === 'PB' ? 'P/B' : acr;
        if (!unsupportedMetrics.includes(displayLabel)) {
          unsupportedMetrics.push(displayLabel);
        }
      }
    }
  }

  // 3. Dynamic entity / ticker non-membership detection
  // Exclude common financial/macro/quarter acronyms from being treated as entities
  const nonEntityAcronyms = new Set([
    'SBV',
    'NHNN',
    'GDP',
    'CPI',
    'VND',
    'USD',
    'Q1',
    'Q2',
    'Q3',
    'Q4',
    'NPL',
    'LLR',
    'ROA',
    'ROE',
    ...candidateMetricAcronyms
  ]);

  // Strategy A: 3-4 letter uppercase tokens in raw query
  const uppercaseTokens = rawQuestion.match(/\b[A-Z]{3,4}\b/g) || [];
  for (const tok of uppercaseTokens) {
    const upper = tok.toUpperCase();
    if (nonEntityAcronyms.has(upper)) continue;
    if (supportedTickers.has(upper)) continue;
    if (!unsupportedEntities.includes(upper)) {
      unsupportedEntities.push(upper);
    }
  }

  // Strategy B: Mentions following entity cues (e.g. "ngân hàng VIB", "cổ phiếu VIB", "mã VIB")
  const entityCueRegex = /(?:ngân hàng|nhà băng|cổ phiếu|mã|bank)\s+([a-zA-Z0-9_]+)/gi;
  let match: RegExpExecArray | null;
  while ((match = entityCueRegex.exec(rawQuestion)) !== null) {
    const candidate = match[1].trim();
    const upper = candidate.toUpperCase();
    const lower = candidate.toLowerCase();
    if (nonEntityAcronyms.has(upper)) continue;
    const isSupported =
      supportedTickers.has(upper) ||
      supportedNames.some((name) => name.includes(lower));
    if (!isSupported && !unsupportedEntities.includes(upper)) {
      unsupportedEntities.push(upper);
    }
  }

  // Strategy C: 3-4 letter tokens ending with bank or ticker-like consonant patterns (vib, ctg, bidv, etc.)
  const words = normalized.split(/[\s,?.!/—–-]+/).filter(Boolean);
  for (const w of words) {
    if (w.length >= 3 && w.length <= 4) {
      const upper = w.toUpperCase();
      if (nonEntityAcronyms.has(upper)) continue;
      if (supportedTickers.has(upper)) continue;
      if (w.endsWith('b') || w.endsWith('v') || w.endsWith('bank') || w === 'ctg') {
        if (!unsupportedEntities.includes(upper)) {
          unsupportedEntities.push(upper);
        }
      }
    }
  }

  const isMismatch =
    unsupportedEntities.length > 0 ||
    unsupportedPeriods.length > 0 ||
    unsupportedMetrics.length > 0;

  const availableCapabilitiesSummary = {
    periods: formatPeriodsSignature(capabilities.periods),
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
