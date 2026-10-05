export function dedupeRunTickers(
  targetTicker?: string | null,
  peerTickers?: (string | null | undefined)[] | null
): string[] {
  const result: string[] = [];
  const seen = new Set<string>();
  const candidates = [targetTicker, ...(peerTickers || [])];

  for (const candidate of candidates) {
    if (typeof candidate !== 'string') continue;
    const normalized = candidate.trim().toUpperCase();
    if (!normalized) continue;
    if (seen.has(normalized)) continue;
    seen.add(normalized);
    result.push(candidate);
  }

  return result;
}
