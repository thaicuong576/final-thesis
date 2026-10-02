/**
 * Normalizes limitations_vi into an array of non-empty strings.
 * The OpenAPI contract declares limitations_vi as a string.
 * This helper tolerates string, string[], or empty/missing values.
 */
export function normalizeLimitations(limitations: unknown): string[] {
  if (limitations == null) {
    return [];
  }
  if (typeof limitations === 'string') {
    const trimmed = limitations.trim();
    return trimmed.length > 0 ? [trimmed] : [];
  }
  if (Array.isArray(limitations)) {
    return limitations
      .map((item) => (typeof item === 'string' ? item.trim() : String(item).trim()))
      .filter((item) => item.length > 0);
  }
  return [];
}
