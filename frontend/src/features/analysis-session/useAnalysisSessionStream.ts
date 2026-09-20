import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { AnalysisSessionEvent, AnalysisSessionViewModel } from './model/types';
import { projectAnalysisSession } from './model/projector';
import type { AnalysisReport } from '../analysis-report';
import { mockCompanyPeerEvents } from './mock/companyPeerEvents';
import { mockCompanyOnlyEvents } from './mock/companyOnlyEvents';
import { mockPeerComparisonReport, mockCompanyOnlyReport } from '../analysis-report/mock/mockReports';

export interface AnalysisStreamRequest {
  query: string;
  target_ticker?: string;
  peer_tickers?: string[];
  period?: string;
}

export type StreamConnectionMode = 'LIVE' | 'MOCK';

export interface RawAnalysisResponseArtifact {
  report_id?: string;
  status?: 'completed' | 'partial' | 'accepted_with_limitations' | 'error';
  query?: string;
  target_ticker?: string;
  peer_tickers?: string[];
  period?: string;
  analysis_plan?: AnalysisReport['analysis_plan'];
  macro_context?: AnalysisReport['macro_context'];
  sector_benchmark?: AnalysisReport['sector_benchmark'];
  company_insights?: AnalysisReport['company_insights'];
  cross_level_critique?: AnalysisReport['cross_level_critique'];
  atomic_claims?: AnalysisReport['atomic_claims'];
  evidence_trail?: AnalysisReport['evidence_trail'];
  revision_summary?: AnalysisReport['revision_summary'];
  limitations?: string[];
}

export interface UseAnalysisSessionStreamOptions {
  request?: AnalysisStreamRequest | null;
  autoStart?: boolean;
  fallbackToMockOnError?: boolean;
  mockEvents?: AnalysisSessionEvent[];
  apiEndpoint?: string;
  onEvent?: (event: AnalysisSessionEvent) => void;
  onComplete?: (report: AnalysisReport) => void;
  onError?: (error: Error) => void;
}

export interface UseAnalysisSessionStreamReturn {
  events: AnalysisSessionEvent[];
  viewModel: AnalysisSessionViewModel;
  isStreaming: boolean;
  isComplete: boolean;
  isError: boolean;
  error: Error | null;
  connectionMode: StreamConnectionMode;
  isMockFallback: boolean;
  backendTarget: string;
  report: AnalysisReport | null;
  startStream: (req?: AnalysisStreamRequest) => Promise<void>;
  cancelStream: () => void;
  retry: () => void;
  switchToMock: () => void;
  switchToLive: () => void;
}

/**
 * Parses a single raw Server-Sent Event (SSE) block formatted as:
 * event: <eventType>
 * data: <jsonPayload>
 */
export function parseSseBlock(block: string): AnalysisSessionEvent | null {
  let eventType = '';
  const dataLines: string[] = [];

  const lines = block.split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('event:')) {
      eventType = trimmed.slice(6).trim();
    } else if (trimmed.startsWith('data:')) {
      dataLines.push(trimmed.slice(5).trim());
    }
  }

  if (dataLines.length === 0) return null;

  try {
    const rawData = dataLines.join('\n');
    const parsed = JSON.parse(rawData) as Partial<AnalysisSessionEvent> & {
      eventId?: string;
      sequence?: number;
      occurredAtMs?: number;
      type?: string;
      payload?: unknown;
    };

    // Backend emits: { eventId, sequence, occurredAtMs, type, payload }
    const type = (eventType || parsed.type) as AnalysisSessionEvent['type'];
    if (!type) return null;

    return {
      eventId: parsed.eventId || `evt-${Math.random().toString(36).substring(2, 9)}`,
      sequence: parsed.sequence ?? 1,
      occurredAtMs: parsed.occurredAtMs ?? 0,
      type,
      payload: parsed.payload ?? parsed
    } as AnalysisSessionEvent;
  } catch (err) {
    console.warn('Failed to parse SSE JSON:', err);
    return null;
  }
}

/**
 * Normalizes an AnalysisResponse artifact into an AnalysisReport.
 */
export function normalizeAnalysisResponseToReport(
  res?: RawAnalysisResponseArtifact | null,
  req?: AnalysisStreamRequest | null
): AnalysisReport {
  const plan = res?.analysis_plan;
  return {
    session_id: res?.report_id || `session-${Date.now()}`,
    report_id: res?.report_id || `rep-${Date.now()}`,
    status: res?.status || 'completed',
    query: res?.query || plan?.query || req?.query || '',
    target_ticker: res?.target_ticker || plan?.target_ticker || req?.target_ticker || 'ACB',
    peer_tickers: res?.peer_tickers || plan?.peer_tickers || req?.peer_tickers || [],
    period: res?.period || plan?.period || req?.period || '2024',
    analysis_plan: {
      plan_id: plan?.plan_id || `plan-${Date.now()}`,
      query: plan?.query || req?.query || '',
      target_ticker: plan?.target_ticker || req?.target_ticker || 'ACB',
      peer_tickers: plan?.peer_tickers || req?.peer_tickers || [],
      period: plan?.period || req?.period || '2024',
      required_capabilities: plan?.required_capabilities || ['company'],
      applicable_links: plan?.applicable_links || [],
      dataset_snapshot_id: plan?.dataset_snapshot_id || 'snap-2024-q4-v1',
      rationale: plan?.rationale || '',
      known_limitations: plan?.known_limitations || []
    },
    macro_context: res?.macro_context ?? null,
    sector_benchmark: res?.sector_benchmark ?? null,
    company_insights: res?.company_insights ?? [],
    cross_level_critique: res?.cross_level_critique ?? [],
    atomic_claims: res?.atomic_claims ?? [],
    evidence_trail: res?.evidence_trail ?? [],
    revision_summary: res?.revision_summary ?? {
      rounds_executed: 0,
      max_rounds: 2,
      status: 'passed',
      reason: '',
      revised_capabilities: []
    },
    limitations: res?.limitations ?? []
  };
}

export const DEFAULT_RENDER_BACKEND = 'https://final-thesis-zgwt.onrender.com';

export function getResolvedApiEndpoint(customEndpoint?: string): string {
  if (customEndpoint) return customEndpoint;
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) {
    const base = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
    return `${base}/api/analyze/stream`;
  }
  return '/api/analyze/stream';
}

export function getBackendTargetDisplay(customEndpoint?: string): string {
  if (customEndpoint && customEndpoint.startsWith('http')) {
    try {
      const url = new URL(customEndpoint);
      return url.origin;
    } catch {
      return customEndpoint;
    }
  }
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  return DEFAULT_RENDER_BACKEND;
}

/**
 * React hook connecting to POST /api/analyze/stream SSE endpoint.
 * Supports progressive event reduction into AnalysisSessionViewModel via projectAnalysisSession.
 * Features automatic and manual fallback to offline mock when backend is unreachable.
 */
export function useAnalysisSessionStream({
  request,
  autoStart = true,
  fallbackToMockOnError = true,
  mockEvents,
  apiEndpoint,
  onEvent,
  onComplete,
  onError
}: UseAnalysisSessionStreamOptions = {}): UseAnalysisSessionStreamReturn {
  const resolvedEndpoint = useMemo(
    () => getResolvedApiEndpoint(apiEndpoint),
    [apiEndpoint]
  );
  const backendTarget = useMemo(
    () => getBackendTargetDisplay(apiEndpoint),
    [apiEndpoint]
  );
  const [connectionMode, setConnectionMode] = useState<StreamConnectionMode>('LIVE');
  const [isMockFallback, setIsMockFallback] = useState(false);
  const [events, setEvents] = useState<AnalysisSessionEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const activeRequest = request ?? null;

  const abortControllerRef = useRef<AbortController | null>(null);

  const switchToMockInternal = useCallback(
    (req?: AnalysisStreamRequest | null) => {
      setConnectionMode('MOCK');
      setIsMockFallback(true);
      setIsError(false);
      setIsStreaming(false);

      const isSolo =
        (req?.peer_tickers && req.peer_tickers.length === 0) ||
        (req?.target_ticker && !req?.peer_tickers);
      const fallbackEvents = mockEvents ?? (isSolo ? mockCompanyOnlyEvents : mockCompanyPeerEvents);
      const fallbackReport = isSolo ? mockCompanyOnlyReport : mockPeerComparisonReport;

      setEvents(fallbackEvents);
      setReport(fallbackReport);
      setIsComplete(true);
      onComplete?.(fallbackReport);
    },
    [mockEvents, onComplete]
  );

  const startStream = useCallback(
    async (requestOverride?: AnalysisStreamRequest) => {
      const targetReq = requestOverride || activeRequest || {
        query: 'So sánh chất lượng tài sản của ACB, TCB và MBB trong năm 2024 và xác định ngân hàng cải thiện rõ nhất.',
        target_ticker: 'ACB',
        peer_tickers: ['TCB', 'MBB'],
        period: '2024'
      };

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      setConnectionMode('LIVE');
      setIsMockFallback(false);
      setIsStreaming(true);
      setIsComplete(false);
      setIsError(false);
      setError(null);
      setEvents([]);
      setReport(null);

      try {
        const payload = {
          query: targetReq.query,
          target_ticker: targetReq.target_ticker,
          peer_tickers: targetReq.peer_tickers ?? [],
          period: targetReq.period ?? '2024'
        };

        const response = await fetch(resolvedEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream'
          },
          body: JSON.stringify(payload),
          signal: controller.signal
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error('ReadableStream not supported or empty response body');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        const accumulatedEvents: AnalysisSessionEvent[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split(/\r?\n\r?\n/);
          buffer = parts.pop() ?? '';

          for (const block of parts) {
            if (!block.trim()) continue;
            const parsedEvent = parseSseBlock(block);
            if (parsedEvent) {
              accumulatedEvents.push(parsedEvent);
              setEvents([...accumulatedEvents]);
              onEvent?.(parsedEvent);

              if (parsedEvent.type === 'REPORT_READY') {
                const rawReport = (parsedEvent.payload as Record<string, unknown>)?.report as
                  | RawAnalysisResponseArtifact
                  | undefined;
                const normalized = normalizeAnalysisResponseToReport(rawReport, targetReq);
                setReport(normalized);
                onComplete?.(normalized);
              }
            }
          }
        }

        // Process any residual in buffer
        if (buffer.trim()) {
          const parsedEvent = parseSseBlock(buffer);
          if (parsedEvent) {
            accumulatedEvents.push(parsedEvent);
            setEvents([...accumulatedEvents]);
            onEvent?.(parsedEvent);

            if (parsedEvent.type === 'REPORT_READY') {
              const rawReport = (parsedEvent.payload as Record<string, unknown>)?.report as
                | RawAnalysisResponseArtifact
                | undefined;
              const normalized = normalizeAnalysisResponseToReport(rawReport, targetReq);
              setReport(normalized);
              onComplete?.(normalized);
            }
          }
        }

        setIsComplete(true);
        setIsStreaming(false);
      } catch (err: unknown) {
        if (controller.signal.aborted) {
          return;
        }
        const errorObj = err instanceof Error ? err : new Error(String(err));
        setError(errorObj);
        setIsError(true);
        setIsStreaming(false);
        onError?.(errorObj);

        if (fallbackToMockOnError) {
          switchToMockInternal(targetReq);
        }
      }
    },
    [activeRequest, resolvedEndpoint, fallbackToMockOnError, onEvent, onComplete, onError, switchToMockInternal]
  );

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const retry = useCallback(() => {
    startStream();
  }, [startStream]);

  const switchToMock = useCallback(() => {
    cancelStream();
    switchToMockInternal(activeRequest);
  }, [cancelStream, switchToMockInternal, activeRequest]);

  const switchToLive = useCallback(() => {
    startStream();
  }, [startStream]);

  useEffect(() => {
    if (!autoStart) return;
    const timer = setTimeout(() => {
      void startStream();
    }, 0);
    return () => {
      clearTimeout(timer);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [autoStart, startStream]);


  const viewModel = useMemo(() => {
    if (events.length === 0) {
      return {
        sessionId: 'session-init',
        rawQuestion: activeRequest?.query || '',
        datasetName: 'Ngân hàng Việt Nam 2024',
        scopeSignature: activeRequest?.target_ticker
          ? `${activeRequest.target_ticker} | ${
              activeRequest.peer_tickers && activeRequest.peer_tickers.length > 0
                ? 'So sánh'
                : 'Độc lập'
            } | ${activeRequest.period || '2024'}`
          : '',
        currentPhase: 'INITIALIZING' as const,
        phaseLabel: 'Đang kết nối luồng phân tích',
        threadItems: [],
        specialistSessions: {},
        invocations: [],
        reportReady: false
      };
    }
    return projectAnalysisSession(events);
  }, [events, activeRequest]);

  return {
    events,
    viewModel,
    isStreaming,
    isComplete,
    isError,
    error,
    connectionMode,
    isMockFallback,
    backendTarget,
    report,
    startStream,
    cancelStream,
    retry,
    switchToMock,
    switchToLive
  };
}
