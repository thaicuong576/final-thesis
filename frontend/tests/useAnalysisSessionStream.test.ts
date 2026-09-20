import { renderHook, act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  parseSseBlock,
  normalizeAnalysisResponseToReport,
  useAnalysisSessionStream,
  type AnalysisStreamRequest
} from '../src/features/analysis-session/useAnalysisSessionStream';

describe('useAnalysisSessionStream Unit & Integration Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // =========================================================================
  // 1. SSE Block Parser Unit Tests
  // =========================================================================
  describe('parseSseBlock', () => {
    it('correctly parses standard single-line SSE frame', () => {
      const sseText = [
        'event: PLAN_CREATED',
        'data: {"eventId":"evt-101","sequence":3,"occurredAtMs":150,"type":"PLAN_CREATED","payload":{"requiredSpecialists":["company","sector"],"planSummary":"Plan created"}}'
      ].join('\n');

      const event = parseSseBlock(sseText);
      expect(event).not.toBeNull();
      expect(event?.type).toBe('PLAN_CREATED');
      expect(event?.eventId).toBe('evt-101');
      expect(event?.sequence).toBe(3);
      expect(event?.occurredAtMs).toBe(150);
      expect(event?.payload).toEqual({
        requiredSpecialists: ['company', 'sector'],
        planSummary: 'Plan created'
      });
    });

    it('correctly parses multi-line SSE data lines', () => {
      const sseText = [
        'event: USER_REQUEST_CONFIRMED',
        'data: {',
        'data:   "eventId": "evt-202",',
        'data:   "sequence": 1,',
        'data:   "occurredAtMs": 50,',
        'data:   "type": "USER_REQUEST_CONFIRMED",',
        'data:   "payload": { "rawQuestion": "Test query" }',
        'data: }'
      ].join('\n');

      const event = parseSseBlock(sseText);
      expect(event).not.toBeNull();
      expect(event?.type).toBe('USER_REQUEST_CONFIRMED');
      expect(event?.eventId).toBe('evt-202');
      expect(event?.sequence).toBe(1);
      expect((event?.payload as { rawQuestion: string }).rawQuestion).toBe('Test query');
    });

    it('infers event type from data JSON when event header is missing', () => {
      const sseText =
        'data: {"eventId":"evt-303","sequence":4,"occurredAtMs":200,"type":"SPECIALIST_STARTED","payload":{"invocationId":"inv-1"}}';

      const event = parseSseBlock(sseText);
      expect(event).not.toBeNull();
      expect(event?.type).toBe('SPECIALIST_STARTED');
      expect(event?.eventId).toBe('evt-303');
    });

    it('returns null for empty blocks or blocks without data', () => {
      expect(parseSseBlock('')).toBeNull();
      expect(parseSseBlock('event: PING\n: comment')).toBeNull();
      expect(parseSseBlock('random text without prefix')).toBeNull();
    });

    it('returns null for invalid JSON payloads without throwing', () => {
      const sseText = 'event: ERROR\ndata: { not valid json }';
      expect(parseSseBlock(sseText)).toBeNull();
    });
  });

  // =========================================================================
  // 2. Report Normalizer Unit Tests
  // =========================================================================
  describe('normalizeAnalysisResponseToReport', () => {
    it('normalizes raw AnalysisResponse from backend into fully-formed AnalysisReport', () => {
      const backendResponse = {
        report_id: 'rep-2024-acb-stream',
        status: 'completed' as const,
        analysis_plan: {
          plan_id: 'plan-1',
          query: 'Phân tích ACB',
          target_ticker: 'ACB',
          peer_tickers: ['TCB'],
          period: '2024',
          required_capabilities: ['company' as const],
          applicable_links: [],
          dataset_snapshot_id: 'snap-1',
          rationale: '',
          known_limitations: []
        },
        company_insights: [
          {
            ticker: 'ACB',
            roe: 21.4,
            nim: 3.82,
            npl: 1.21,
            cir: 31.8,
            casa: 23.2,
            car: 12.8,
            ldr: 82.5,
            assessment: 'ACB tang truong ben vung'
          }
        ]
      };

      const normalized = normalizeAnalysisResponseToReport(backendResponse);
      expect(normalized.report_id).toBe('rep-2024-acb-stream');
      expect(normalized.status).toBe('completed');
      expect(normalized.target_ticker).toBe('ACB');
      expect(normalized.peer_tickers).toEqual(['TCB']);
      expect(normalized.period).toBe('2024');
      expect(normalized.company_insights).toHaveLength(1);
      expect(normalized.atomic_claims).toEqual([]);
      expect(normalized.revision_summary.status).toBe('passed');
    });
  });

  // =========================================================================
  // 3. useAnalysisSessionStream Hook Integration Tests
  // =========================================================================
  describe('useAnalysisSessionStream', () => {
    function createMockStream(chunks: string[]) {
      const encoder = new TextEncoder();
      let index = 0;

      const stream = new ReadableStream<Uint8Array>({
        pull(controller) {
          if (index < chunks.length) {
            controller.enqueue(encoder.encode(chunks[index]));
            index++;
          } else {
            controller.close();
          }
        }
      });

      return stream;
    }

    it('progressively receives SSE events and reduces them into viewModel', async () => {
      const chunk1 =
        'event: USER_REQUEST_CONFIRMED\ndata: {"eventId":"evt-1","sequence":1,"occurredAtMs":50,"type":"USER_REQUEST_CONFIRMED","payload":{"rawQuestion":"Phan tich ACB","datasetName":"Ngân hàng Việt Nam 2024","scopeSignature":"ACB | Độc lập | 2024"}}\n\n' +
        'event: PLANNING_STARTED\ndata: {"eventId":"evt-2","sequence":2,"occurredAtMs":100,"type":"PLANNING_STARTED","payload":{"message":"Dang lap ke hoach"}}\n\n';

      const chunk2 =
        'event: PLAN_CREATED\ndata: {"eventId":"evt-3","sequence":3,"occurredAtMs":150,"type":"PLAN_CREATED","payload":{"requiredSpecialists":["company"],"message":"Da kich hoat Doanh nghiep"}}\n\n' +
        'event: REPORT_READY\ndata: {"eventId":"evt-4","sequence":4,"occurredAtMs":300,"type":"REPORT_READY","payload":{"message":"Bao cao san sang","reportId":"rep-acb-test","report":{"report_id":"rep-acb-test","status":"completed","target_ticker":"ACB","peer_tickers":[],"period":"2024","company_insights":[]}}}\n\n';

      const mockResponseStream = createMockStream([chunk1, chunk2]);

      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        body: mockResponseStream
      } as unknown as Response);

      const request: AnalysisStreamRequest = {
        query: 'Phân tích ACB',
        target_ticker: 'ACB',
        peer_tickers: [],
        period: '2024'
      };

      const onEventMock = vi.fn();
      const onCompleteMock = vi.fn();

      const { result } = renderHook(() =>
        useAnalysisSessionStream({
          request,
          autoStart: true,
          fallbackToMockOnError: false,
          onEvent: onEventMock,
          onComplete: onCompleteMock
        })
      );

      // Verify initial streaming state
      expect(result.current.connectionMode).toBe('LIVE');

      await waitFor(() => {
        expect(result.current.isComplete).toBe(true);
      });

      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/analyze/stream',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream'
          }
        })
      );

      // Verify all 4 events were received
      expect(result.current.events).toHaveLength(4);
      expect(onEventMock).toHaveBeenCalledTimes(4);

      // Verify viewModel was updated through pure projector
      expect(result.current.viewModel.currentPhase).toBe('READY_FOR_REPORT');
      expect(result.current.viewModel.reportReady).toBe(true);

      // Verify report was extracted and passed to onComplete
      expect(result.current.report).not.toBeNull();
      expect(result.current.report?.report_id).toBe('rep-acb-test');
      expect(onCompleteMock).toHaveBeenCalledWith(
        expect.objectContaining({
          report_id: 'rep-acb-test'
        })
      );
    });

    it('gracefully handles network error by falling back to mock mode when fallbackToMockOnError=true', async () => {
      const fetchSpy = vi
        .spyOn(globalThis, 'fetch')
        .mockRejectedValue(new Error('Failed to fetch'));

      const onErrorMock = vi.fn();

      const { result } = renderHook(() =>
        useAnalysisSessionStream({
          request: {
            query: 'So sánh ACB và TCB',
            target_ticker: 'ACB',
            peer_tickers: ['TCB'],
            period: '2024'
          },
          autoStart: true,
          fallbackToMockOnError: true,
          onError: onErrorMock
        })
      );

      await waitFor(() => {
        expect(result.current.connectionMode).toBe('MOCK');
      });

      expect(fetchSpy).toHaveBeenCalled();
      expect(onErrorMock).toHaveBeenCalled();
      expect(result.current.isMockFallback).toBe(true);
      expect(result.current.events.length).toBeGreaterThan(0);
      expect(result.current.report).not.toBeNull();
      expect(result.current.viewModel.reportReady).toBe(true);
    });

    it('supports manual switching between Live and Mock modes', async () => {
      vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}));

      const { result } = renderHook(() =>
        useAnalysisSessionStream({
          request: { query: 'Test', target_ticker: 'ACB' },
          autoStart: true,
          fallbackToMockOnError: false
        })
      );

      expect(result.current.connectionMode).toBe('LIVE');

      act(() => {
        result.current.switchToMock();
      });

      expect(result.current.connectionMode).toBe('MOCK');
      expect(result.current.isMockFallback).toBe(true);
      expect(result.current.events.length).toBeGreaterThan(0);

      act(() => {
        result.current.switchToLive();
      });

      expect(result.current.connectionMode).toBe('LIVE');
    });
  });
});
