import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  parseSseBlock,
  normalizeAnalysisResponseToReport,
  useAnalysisSessionStream,
  type AnalysisStreamRequest
} from '../src/features/analysis-session/useAnalysisSessionStream';

describe('parseSseBlock', () => {
  it('parses the API event envelope and payload', () => {
    const event = parseSseBlock(
      'event: REPORT_READY\ndata: {"eventId":"evt-1","sequence":2,"occurredAtMs":20,"type":"REPORT_READY","payload":{"report":{"report_id":"r-1","status":"partial"}}}'
    );

    expect(event).toMatchObject({
      eventId: 'evt-1',
      sequence: 2,
      type: 'REPORT_READY',
      payload: { report: { report_id: 'r-1', status: 'partial' } }
    });
  });

  it('returns null for empty or invalid event blocks', () => {
    expect(parseSseBlock('')).toBeNull();
    expect(parseSseBlock('event: ping')).toBeNull();
    expect(parseSseBlock('event: ERROR\ndata: {bad json}')).toBeNull();
  });
});

describe('normalizeAnalysisResponseToReport', () => {
  it('preserves the partial API response and only fills request fields that were sent', () => {
    const normalized = normalizeAnalysisResponseToReport(
      {
        report_id: 'rep-live-1',
        status: 'partial',
        atomic_claims: [
          {
            claim_id: 'claim-1',
            capability: 'company',
            statement: 'ROE observation',
            claim_type: 'factual_observation',
            evidence_refs: ['ev-1'],
            confidence: 0.8,
            stage1_status: 'accepted',
            stage2_critique_status: null
          }
        ],
        evidence_trail: [
          {
            evidence_id: 'ev-1',
            metric: 'ROE',
            ticker: 'ACB',
            period: '2024_Q4',
            value: 12,
            source_doc: 'https://example.test/source.pdf',
            table_locator: 'page 12'
          }
        ]
      },
      { query: 'ROE của ACB trong năm 2024', target_ticker: 'ACB', period: '2024' }
    );

    expect(normalized).toMatchObject({
      report_id: 'rep-live-1',
      status: 'partial',
      query: 'ROE của ACB trong năm 2024',
      target_ticker: 'ACB',
      period: '2024',
      analysis_plan: null,
      atomic_claims: [{ stage1_status: 'accepted', stage2_critique_status: null }],
      evidence_trail: [{ evidence_id: 'ev-1', table_locator: 'page 12' }]
    });
    expect(normalized.company_insights).toBeUndefined();
    expect(normalized.revision_summary).toBeUndefined();
  });

  it('accepts the composite API DTO when optional analysis fields are explicitly unknown', () => {
    const normalized = normalizeAnalysisResponseToReport({
      report_id: 'rep-live-2',
      status: 'partial',
      analysis_plan: {
        plan_id: 'plan-live-2',
        query: 'Phân tích ROE của ACB trong năm 2024',
        target_ticker: 'ACB',
        peer_tickers: [],
        period: null,
        required_capabilities: ['company'],
        applicable_links: [],
        dataset_snapshot_id: 'snapshot-2',
        rationale: null,
        known_limitations: ['Stage 2 was not run.']
      },
      atomic_claims: [{
        claim_id: 'claim-2',
        capability: 'company',
        statement: 'ROE observation',
        claim_type: 'factual_observation',
        evidence_refs: ['ev-2'],
        confidence: null,
        stage1_status: 'accepted',
        stage2_critique_status: null
      }]
    });

    expect(normalized.analysis_plan?.period).toBeNull();
    expect(normalized.analysis_plan?.rationale).toBeNull();
    expect(normalized.atomic_claims?.[0].confidence).toBeNull();
  });

  it('rejects a response without an API report id', () => {
    expect(() => normalizeAnalysisResponseToReport({ status: 'partial' })).toThrow(/mã báo cáo/i);
  });
});

describe('useAnalysisSessionStream', () => {
  beforeEach(() => vi.restoreAllMocks());

  function createMockStream(chunks: string[]) {
    const encoder = new TextEncoder();
    let index = 0;
    return new ReadableStream<Uint8Array>({
      pull(controller) {
        if (index < chunks.length) controller.enqueue(encoder.encode(chunks[index++]));
        else controller.close();
      }
    });
  }

  it('opens a report only from an API REPORT_READY artifact', async () => {
    const stream = createMockStream([
      'event: REPORT_READY\ndata: {"eventId":"evt-1","sequence":1,"occurredAtMs":10,"type":"REPORT_READY","payload":{"report":{"report_id":"rep-1","status":"partial"}}}\n\n'
    ]);
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body: stream
    } as unknown as Response);
    const onComplete = vi.fn();
    const request: AnalysisStreamRequest = {
      query: 'Phân tích ROE của ACB trong năm 2024',
      target_ticker: 'ACB',
      peer_tickers: [],
      period: '2024'
    };

    const { result } = renderHook(() => useAnalysisSessionStream({ request, onComplete }));

    await waitFor(() => expect(result.current.isComplete).toBe(true));
    expect(fetchSpy).toHaveBeenCalledWith('/api/analyze/stream', expect.objectContaining({ method: 'POST' }));
    expect(result.current.report).toMatchObject({ report_id: 'rep-1', status: 'partial' });
    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ report_id: 'rep-1', status: 'partial' }));
  });

  it('reports connection errors without creating mock events or a report', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'));
    const onError = vi.fn();
    const request = { query: 'ROE của ACB' };
    const { result } = renderHook(() => useAnalysisSessionStream({ request, onError }));

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(fetchSpy).toHaveBeenCalledOnce();
    expect(onError).toHaveBeenCalledOnce();
    expect(result.current.events).toEqual([]);
    expect(result.current.report).toBeNull();
    expect(result.current.isComplete).toBe(false);
    expect(result.current.viewModel.reportReady).toBe(false);
  });

  it('treats stream closure without REPORT_READY as an error, not completion', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body: createMockStream(['event: PLANNING_STARTED\ndata: {"type":"PLANNING_STARTED"}\n\n'])
    } as unknown as Response);
    const request = { query: 'ROE của ACB' };
    const { result } = renderHook(() => useAnalysisSessionStream({ request }));

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.isComplete).toBe(false);
    expect(result.current.report).toBeNull();
  });

  it('treats stream closure with RUN_BLOCKED as a blocked terminal completion, not an error', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body: createMockStream([
        'event: RUN_BLOCKED\ndata: {"eventId":"evt-blk-1","sequence":1,"occurredAtMs":10,"type":"RUN_BLOCKED","payload":{"reason":"unsupported_period: Period 2024 is not an exact period in the accepted snapshot."}}\n\n'
      ])
    } as unknown as Response);
    const request = { query: 'Phân tích LLR_COVERAGE của ACB trong năm 2024' };
    const { result } = renderHook(() => useAnalysisSessionStream({ request }));

    await waitFor(() => expect(result.current.isComplete).toBe(true));
    expect(result.current.isError).toBe(false);
    expect(result.current.isBlocked).toBe(true);
    expect(result.current.report).toBeNull();
    expect(result.current.viewModel.currentPhase).toBe('BLOCKED');
  });

  it('shows configured endpoint details', () => {
    const { result } = renderHook(() => useAnalysisSessionStream({
      apiEndpoint: 'https://custom-api.example/api/analyze/stream',
      autoStart: false
    }));
    expect(result.current.backendTarget).toBe('https://custom-api.example');
  });
});
