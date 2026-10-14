import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AnalysisSessionWorkspace } from '../src/features/analysis-session/components/AnalysisSessionWorkspace';
import type { TraceStep } from '../src/features/analysis-session/model/types';
import traceFixture from '../src/test/fixtures/er-trace-acb-2024q4.json';

function createMockStream(chunks: string[]) {
  const encoder = new TextEncoder();
  let index = 0;
  return new ReadableStream<Uint8Array>({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index++]));
      } else {
        controller.close();
      }
    }
  });
}

describe('AnalysisSessionWorkspace (ER-6 Trace and Board)', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('renders fixture steps without network fetch when steps prop is provided', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const steps = traceFixture.steps as unknown as TraceStep[];

    render(
      <MemoryRouter>
        <AnalysisSessionWorkspace
          isLiveStream={false}
          steps={steps}
          streamRequest={{ query: traceFixture.query }}
        />
      </MemoryRouter>
    );

    expect(screen.getByRole('region', { name: 'Điều phối viên' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Company' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Sector' })).toBeInTheDocument();
    expect(screen.getByText('Quá trình phân tích')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /Mở báo cáo/i })[0]).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('connects to live stream and shows report button on report_ready', async () => {
    const stream = createMockStream([
      `event: TRACE_STEP\ndata: ${JSON.stringify({
        step_id: 't-1',
        seq: 1,
        t_ms: 100,
        actor: 'orchestrator',
        kind: 'plan',
        summary: 'Lập kế hoạch',
        detail: {
          question_type: 'company_profile',
          agents: [{ agent: 'company', decision: 'run' }]
        }
      })}\n\n`,
      `event: TRACE_STEP\ndata: ${JSON.stringify({
        step_id: 't-2',
        seq: 2,
        t_ms: 500,
        actor: 'orchestrator',
        kind: 'report_ready',
        summary: 'Báo cáo sẵn sàng',
        detail: { report_id: 'rep-live-test' }
      })}\n\n`
    ]);

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      body: stream
    } as unknown as Response);

    const onViewReport = vi.fn();

    render(
      <MemoryRouter>
        <AnalysisSessionWorkspace
          isLiveStream={true}
          streamRequest={{ query: 'Phân tích ROE của ACB' }}
          onViewReport={onViewReport}
        />
      </MemoryRouter>
    );

    expect((await screen.findAllByRole('button', { name: /Mở báo cáo/i }))[0]).toBeInTheDocument();
  });

  it('displays connection error and retry button on fetch failure without creating mock events', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'));

    render(
      <MemoryRouter>
        <AnalysisSessionWorkspace
          isLiveStream={true}
          streamRequest={{ query: 'Phân tích ROE của ACB' }}
        />
      </MemoryRouter>
    );

    expect(await screen.findByText('Mất kết nối. Thử lại')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Thử lại/i })).toBeInTheDocument();
  });

  it('handles legacy SSE stream with only REPORT_READY without throwing disconnect error', async () => {
    const stream = createMockStream([
      `event: REPORT_READY\ndata: ${JSON.stringify({
        reportId: 'rep-legacy-done',
        status: 'completed'
      })}\n\n`
    ]);

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      body: stream
    } as unknown as Response);

    const onViewReport = vi.fn();

    render(
      <MemoryRouter>
        <AnalysisSessionWorkspace
          isLiveStream={true}
          streamRequest={{ query: 'Phân tích ROE của ACB' }}
          onViewReport={onViewReport}
        />
      </MemoryRouter>
    );

    expect((await screen.findAllByRole('button', { name: /Mở báo cáo/i }))[0]).toBeInTheDocument();
    expect(screen.queryByText(/Mất kết nối/i)).not.toBeInTheDocument();
  });

  it('handles legacy SSE stream with only RUN_BLOCKED without throwing disconnect error', async () => {
    const onBlocked = vi.fn();
    const stream = createMockStream([
      `event: RUN_BLOCKED\ndata: ${JSON.stringify({
        status: 'error',
        reason: 'unsupported_metric',
        error: {
          code: 'unsupported_metric',
          message: 'Chỉ tiêu phân tích chưa được hỗ trợ.'
        }
      })}\n\n`
    ]);

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      body: stream
    } as unknown as Response);

    render(
      <MemoryRouter>
        <AnalysisSessionWorkspace
          isLiveStream={true}
          streamRequest={{ query: 'Phân tích chỉ tiêu lạ' }}
          onBlocked={onBlocked}
        />
      </MemoryRouter>
    );

    await vi.waitFor(() => {
      expect(onBlocked).toHaveBeenCalledWith(
        expect.objectContaining({
          code: 'unsupported_metric',
          message: 'Chỉ tiêu phân tích chưa được hỗ trợ.'
        })
      );
    });
    expect(screen.queryByText(/Mất kết nối/i)).not.toBeInTheDocument();
  });

  it('triggers onBackToComposer when clicking back button', async () => {
    const onBack = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <AnalysisSessionWorkspace
          isLiveStream={false}
          steps={[]}
          onBackToComposer={onBack}
        />
      </MemoryRouter>
    );

    const backBtn = screen.getByRole('button', { name: /Quay lại trang hỏi/i });
    await user.click(backBtn);
    expect(onBack).toHaveBeenCalledOnce();
  });
});
