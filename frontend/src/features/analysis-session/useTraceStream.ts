import { useCallback, useEffect, useRef, useState } from 'react';
import type { TraceStep } from './model/types';
import { getApiBaseUrl } from '@/shared/lib/apiUrl';

export interface UseTraceStreamOptions {
  request?: { query: string } | null;
  autoStart?: boolean;
  apiEndpoint?: string;
  initialSteps?: TraceStep[];
  onStep?: (step: TraceStep) => void;
  onReportReady?: (reportId: string) => void;
  onBlocked?: (info: { code?: string; message: string; suggestions?: string[] }) => void;
  onError?: (error: Error) => void;
}

export interface UseTraceStreamReturn {
  steps: TraceStep[];
  isStreaming: boolean;
  isComplete: boolean;
  isBlocked: boolean;
  blockedInfo: { code?: string; message: string; suggestions?: string[] } | null;
  isDisconnected: boolean;
  error: Error | null;
  reportId: string | null;
  startStream: (req?: { query: string }) => Promise<void>;
  cancelStream: () => void;
  retry: () => void;
}

export const ERROR_CODE_MESSAGES: Record<string, string> = {
  unsupported_period: 'Giai đoạn phân tích chưa được hỗ trợ.',
  unsupported_metric: 'Chỉ tiêu phân tích chưa được hỗ trợ.',
  unsupported_entity: 'Ngân hàng được yêu cầu chưa nằm trong danh mục hỗ trợ.',
  target_entity_required: 'Vui lòng nêu rõ ngân hàng cần phân tích.',
  metric_required: 'Vui lòng chọn hoặc nêu ít nhất một chỉ tiêu phân tích.',
  unsupported_macro_scope: 'Dữ liệu kinh tế vĩ mô chưa sẵn sàng cho kỳ phân tích này.',
};

export function mapErrorCodeToMessage(code?: string): string {
  if (!code) return 'Hệ thống chưa trả lời được câu hỏi này.';
  const cleanCode = code.split(':')[0].trim().toLowerCase();
  return ERROR_CODE_MESSAGES[cleanCode] || 'Hệ thống chưa trả lời được câu hỏi này.';
}

/**
 * Parses a single raw Server-Sent Event (SSE) block for TRACE_STEP, REPORT_READY, or RUN_BLOCKED events.
 * Ignores legacy intermediate events without throwing errors.
 */
export function parseTraceSseBlock(block: string): TraceStep | null {
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
    const parsed = JSON.parse(rawData) as Record<string, unknown>;
    const resolvedType = eventType || (parsed.type as string) || '';

    // Case 1: event is TRACE_STEP
    if (resolvedType === 'TRACE_STEP') {
      const payload = (parsed.payload ?? parsed) as Record<string, unknown>;
      if (payload && typeof payload.step_id === 'string' && typeof payload.kind === 'string') {
        return payload as unknown as TraceStep;
      }
    }

    // Case 2: event is REPORT_READY
    if (resolvedType === 'REPORT_READY') {
      const payload = (parsed.payload ?? parsed) as Record<string, unknown>;
      const reportId = (payload.reportId ||
        payload.report_id ||
        parsed.reportId ||
        parsed.report_id ||
        (payload.report as Record<string, unknown>)?.report_id ||
        '') as string;
      return {
        step_id: (parsed.eventId as string) || `step-report-ready-${Date.now()}`,
        seq: (parsed.sequence as number) || 999,
        t_ms: (parsed.occurredAtMs as number) || 0,
        kind: 'report_ready',
        actor: 'orchestrator',
        recipient: null,
        summary: 'Báo cáo sẵn sàng',
        detail: { report_id: reportId }
      };
    }

    // Case 3: event is RUN_BLOCKED
    if (resolvedType === 'RUN_BLOCKED') {
      const payload = (parsed.payload ?? parsed) as Record<string, unknown>;
      const errorObj = (payload.error as Record<string, unknown>) || {};
      const rawCode = (errorObj.code || payload.reason || payload.code) as string | undefined;
      const code = rawCode ? rawCode.split(':')[0].trim() : undefined;
      const rawMsg = (errorObj.message || payload.message) as string | undefined;
      const message = rawMsg || mapErrorCodeToMessage(code);
      const suggestions = (errorObj.suggestions || payload.suggestions) as string[] | undefined;

      return {
        step_id: (parsed.eventId as string) || `step-blocked-${Date.now()}`,
        seq: (parsed.sequence as number) || 999,
        t_ms: (parsed.occurredAtMs as number) || 0,
        kind: 'blocked',
        actor: 'system',
        recipient: null,
        summary: 'Yêu cầu bị chặn',
        detail: { code, message, suggestions }
      };
    }

    // Case 4: parsed data directly matches TraceStep contract
    if (typeof parsed.step_id === 'string' && typeof parsed.kind === 'string' && typeof parsed.actor === 'string') {
      return parsed as unknown as TraceStep;
    }

    return null;
  } catch {
    return null;
  }
}

export function useTraceStream({
  request,
  autoStart = true,
  apiEndpoint,
  initialSteps,
  onStep,
  onReportReady,
  onBlocked,
  onError
}: UseTraceStreamOptions = {}): UseTraceStreamReturn {
  const [steps, setSteps] = useState<TraceStep[]>(initialSteps ?? []);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [isBlocked, setIsBlocked] = useState(false);
  const [blockedInfo, setBlockedInfo] = useState<{ code?: string; message: string; suggestions?: string[] } | null>(null);
  const [isDisconnected, setIsDisconnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);

  const query = request?.query?.trim() ?? '';
  const abortControllerRef = useRef<AbortController | null>(null);

  const getEndpoint = useCallback(() => {
    if (apiEndpoint) return apiEndpoint;
    const base = getApiBaseUrl();
    return base ? `${base}/api/analyze/stream` : '/api/analyze/stream';
  }, [apiEndpoint]);

  const startStream = useCallback(
    async (requestOverride?: { query: string }) => {
      const targetQuery = requestOverride?.query?.trim() ?? query;

      if (!targetQuery) {
        const err = new Error('Chưa có câu hỏi được xác nhận để gửi tới API.');
        setError(err);
        setIsDisconnected(true);
        setIsStreaming(false);
        return;
      }

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      setIsStreaming(true);
      setIsComplete(false);
      setIsBlocked(false);
      setBlockedInfo(null);
      setIsDisconnected(false);
      setError(null);
      setSteps([]);
      setReportId(null);

      const accumulatedSteps: TraceStep[] = [];

      try {
        const response = await fetch(getEndpoint(), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream'
          },
          body: JSON.stringify({ query: targetQuery }),
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

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split(/\r?\n\r?\n/);
          buffer = parts.pop() ?? '';

          for (const block of parts) {
            if (!block.trim()) continue;
            const parsedStep = parseTraceSseBlock(block);
            if (parsedStep) {
              accumulatedSteps.push(parsedStep);
              setSteps([...accumulatedSteps]);
              onStep?.(parsedStep);

              if (parsedStep.kind === 'report_ready') {
                const repId = (parsedStep.detail?.report_id as string) || '';
                if (repId) {
                  setReportId(repId);
                  onReportReady?.(repId);
                }
              } else if (parsedStep.kind === 'blocked') {
                const info = {
                  code: parsedStep.detail?.code as string | undefined,
                  message: (parsedStep.detail?.message as string) || 'Yêu cầu bị chặn.',
                  suggestions: parsedStep.detail?.suggestions as string[] | undefined
                };
                setIsBlocked(true);
                setBlockedInfo(info);
                onBlocked?.(info);
              }
            }
          }
        }

        // Residual buffer
        if (buffer.trim()) {
          const parsedStep = parseTraceSseBlock(buffer);
          if (parsedStep) {
            accumulatedSteps.push(parsedStep);
            setSteps([...accumulatedSteps]);
            onStep?.(parsedStep);

            if (parsedStep.kind === 'report_ready') {
              const repId = (parsedStep.detail?.report_id as string) || '';
              if (repId) {
                setReportId(repId);
                onReportReady?.(repId);
              }
            } else if (parsedStep.kind === 'blocked') {
              const info = {
                code: parsedStep.detail?.code as string | undefined,
                message: (parsedStep.detail?.message as string) || 'Yêu cầu bị chặn.',
                suggestions: parsedStep.detail?.suggestions as string[] | undefined
              };
              setIsBlocked(true);
              setBlockedInfo(info);
              onBlocked?.(info);
            }
          }
        }

        const hasReportReady = accumulatedSteps.some((s) => s.kind === 'report_ready');
        const hasBlocked = accumulatedSteps.some((s) => s.kind === 'blocked');

        if (!hasReportReady && !hasBlocked) {
          throw new Error('Mất kết nối. Thử lại');
        }

        setIsComplete(true);
        setIsStreaming(false);
      } catch (err: unknown) {
        if (controller.signal.aborted) {
          return;
        }
        if (accumulatedSteps.some((s) => s.kind === 'blocked' || s.kind === 'report_ready')) {
          setIsComplete(true);
          setIsStreaming(false);
          return;
        }
        const errorObj = err instanceof Error ? err : new Error(String(err));
        setError(errorObj);
        setIsDisconnected(true);
        setIsStreaming(false);
        onError?.(errorObj);
      }
    },
    [query, getEndpoint, onStep, onReportReady, onBlocked, onError]
  );

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsStreaming(false);
  }, []);

  const retry = useCallback(() => {
    void startStream();
  }, [startStream]);

  useEffect(() => {
    let unmounted = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    if (autoStart && query) {
      timer = setTimeout(() => {
        if (!unmounted) {
          void startStream();
        }
      }, 0);
    }

    return () => {
      unmounted = true;
      if (timer) clearTimeout(timer);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [autoStart, query, startStream]);

  return {
    steps,
    isStreaming,
    isComplete,
    isBlocked,
    blockedInfo,
    isDisconnected,
    error,
    reportId,
    startStream,
    cancelStream,
    retry
  };
}
