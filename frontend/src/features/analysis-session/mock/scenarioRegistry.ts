import type { AnalysisSessionEvent } from '../model/types';
import { mockCompanyOnlyEvents } from './companyOnlyEvents';
import { mockCompanyPeerEvents } from './companyPeerEvents';
import { mockTargetedRevisionEvents } from './targetedRevisionEvents';
import { mockMacroCompanyEvents } from './macroCompanyEvents';
import type { ParseResult } from '../../analysis-composer/model/types';

export type CanonicalScenarioKey =
  | 'company-only'
  | 'company-peer'
  | 'targeted-revision'
  | 'macro-company';

export const SCENARIO_FIXTURES: Record<CanonicalScenarioKey, AnalysisSessionEvent[]> = {
  'company-only': mockCompanyOnlyEvents,
  'company-peer': mockCompanyPeerEvents,
  'targeted-revision': mockTargetedRevisionEvents,
  'macro-company': mockMacroCompanyEvents
};

export function resolveScenarioKey(inputKey?: string | null): CanonicalScenarioKey {
  if (!inputKey) return 'company-only';
  const lower = inputKey.toLowerCase().replace(/_/g, '-');
  if (lower.includes('targeted') || lower.includes('revision') || lower === 'c') {
    return 'targeted-revision';
  }
  if (lower.includes('macro') || lower === 'd') {
    return 'macro-company';
  }
  if (lower.includes('peer') || lower === 'b') {
    return 'company-peer';
  }
  return 'company-only';
}

export function getScenarioEvents(key?: string | null): AnalysisSessionEvent[] {
  const canonical = resolveScenarioKey(key);
  return SCENARIO_FIXTURES[canonical];
}

/**
 * Maps an interpreted ParseResult from Screen 1 to the most appropriate
 * deterministic scenario event fixture.
 */
export function getEventsForParseResult(
  parseResult: ParseResult,
  options: { withTargetedRevision?: boolean } = {}
): AnalysisSessionEvent[] {
  const selectedCapIds = parseResult.scope.analysisPlan.selectedCapabilities.map((c) => c.id);

  const hasPeer = selectedCapIds.includes('peer');
  const hasMacro = selectedCapIds.includes('macro');

  if (options.withTargetedRevision && hasPeer) {
    return mockTargetedRevisionEvents;
  }
  if (hasMacro) {
    return mockMacroCompanyEvents;
  }
  if (hasPeer) {
    return mockCompanyPeerEvents;
  }
  return mockCompanyOnlyEvents;
}
