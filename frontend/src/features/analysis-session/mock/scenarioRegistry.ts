import type { AnalysisSessionEvent } from '../model/types';
import { mockCompanyOnlyEvents } from './companyOnlyEvents';
import { mockCompanyPeerEvents } from './companyPeerEvents';
import { mockTargetedRevisionEvents } from './targetedRevisionEvents';
import { mockMacroCompanyEvents } from './macroCompanyEvents';
import type { ParseResult } from '../../analysis-composer/model/types';

import { buildMockEventsFromParseResult } from './dynamicEventGenerator';
export { buildMockEventsFromParseResult } from './dynamicEventGenerator';

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
 * Maps an interpreted ParseResult from Screen 1 to an event-sourced mock stream.
 * Dynamically builds events matching the confirmed question and scope to prevent silent scope substitution.
 */
export function getEventsForParseResult(parseResult: ParseResult): AnalysisSessionEvent[] {
  return buildMockEventsFromParseResult(parseResult);
}
