export interface AnalysisStreamRequest {
  query: string;
  target_ticker?: string;
  peer_tickers?: string[];
  period?: string;
}

export type SupportedStreamRequest =
  | { request: AnalysisStreamRequest; reason: null }
  | { request: null; reason: string };

/**
 * Lean request builder: removes all client-side blocking (periods, metrics, capabilities).
 * The query is sent as-is; the backend is the sole authority for planning and validation.
 */
export function buildSupportedStreamRequest(question: string): SupportedStreamRequest {
  const trimmed = question.trim();
  if (!trimmed) {
    return {
      request: null,
      reason: 'Vui lòng nhập câu hỏi phân tích.'
    };
  }

  return {
    request: { query: trimmed },
    reason: null
  };
}
