import type { AnalysisCapabilities } from '@/entities/capability/model/types';
import { formatQuarter } from '@/entities/capability/model/coverage';

/**
 * Formats a raw period ID (e.g. "2025_Q4", "2024-Q1") into a Vietnamese quarter string
 * (e.g. "quý 4/2025"). Uses formatQuarter from coverage.ts. Returns null if missing or unparseable.
 */
export function formatQuarterVi(periodId?: string | null): string | null {
  if (!periodId || typeof periodId !== 'string') return null;
  const formatted = formatQuarter(periodId.trim());
  const match = /^Q([1-4])\/(\d{4})$/i.exec(formatted);
  return match ? `quý ${match[1]}/${match[2]}` : null;
}

/**
 * Identifies the first bank from the served dataset (capabilities) that is not the target entity.
 */
export function findFirstPeer(
  entity: string,
  capabilities?: AnalysisCapabilities | { entities?: Array<{ id?: string; ticker?: string; name?: string }> } | null
): string | null {
  if (!capabilities) return null;

  const normalizedE = entity.trim().toUpperCase();

  if (Array.isArray(capabilities.entities)) {
    for (const ent of capabilities.entities) {
      const code = (ent.ticker || ent.id || '').trim();
      if (code && code.toUpperCase() !== normalizedE) {
        return code;
      }
    }
  }

  const peerUniverse = (capabilities as AnalysisCapabilities).peerUniverse;
  if (peerUniverse && Array.isArray(peerUniverse.entityIds)) {
    for (const id of peerUniverse.entityIds) {
      const code = (id || '').trim();
      if (code && code.toUpperCase() !== normalizedE) {
        return code;
      }
    }
  }

  return null;
}

export interface BuildUploadSuggestionsParams {
  entity: string;
  periodId?: string | null;
  capabilities?: AnalysisCapabilities | { entities?: Array<{ id?: string; ticker?: string; name?: string }> } | null;
}

/**
 * Shared pure function to generate analysis suggestions for an uploaded bank.
 * Suggestions format:
 * 1. Tỷ lệ nợ xấu của E quý Q/Y là bao nhiêu?
 * 2. Sức khỏe tài chính của E quý Q/Y so với nhóm
 * 3. So sánh E và <peer> quý Q/Y (omitted if no peer available)
 *
 * If period is missing or cannot be parsed, suggestions omit the period phrase.
 */
export function buildUploadSuggestions(
  entityOrParams: string | BuildUploadSuggestionsParams,
  periodId?: string | null,
  capabilities?: AnalysisCapabilities | { entities?: Array<{ id?: string; ticker?: string; name?: string }> } | null
): string[] {
  let entity: string;
  let period: string | null | undefined;
  let caps: AnalysisCapabilities | { entities?: Array<{ id?: string; ticker?: string; name?: string }> } | null | undefined;

  if (typeof entityOrParams === 'object' && entityOrParams !== null) {
    entity = entityOrParams.entity;
    period = entityOrParams.periodId;
    caps = entityOrParams.capabilities;
  } else {
    entity = entityOrParams;
    period = periodId;
    caps = capabilities;
  }

  const e = (entity || '').trim();
  if (!e) return [];

  const periodPhrase = formatQuarterVi(period);
  const peer = findFirstPeer(e, caps);

  const suggestions: string[] = [];

  // Suggestion 1: Tỷ lệ nợ xấu của E [quý Q/Y] là bao nhiêu?
  suggestions.push(
    periodPhrase
      ? `Tỷ lệ nợ xấu của ${e} ${periodPhrase} là bao nhiêu?`
      : `Tỷ lệ nợ xấu của ${e} là bao nhiêu?`
  );

  // Suggestion 2: Sức khỏe tài chính của E [quý Q/Y] so với nhóm
  suggestions.push(
    periodPhrase
      ? `Sức khỏe tài chính của ${e} ${periodPhrase} so với nhóm`
      : `Sức khỏe tài chính của ${e} so với nhóm`
  );

  // Suggestion 3: So sánh E và <peer> [quý Q/Y] (omitted if no peer)
  if (peer) {
    suggestions.push(
      periodPhrase
        ? `So sánh ${e} và ${peer} ${periodPhrase}`
        : `So sánh ${e} và ${peer}`
    );
  }

  return suggestions;
}
