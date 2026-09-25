import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AnalysisSessionWorkspace, projectAnalysisSession, mockCompanyOnlyEvents } from '../src/features/analysis-session';

function reportStream(report?: Record<string, unknown>) {
  const encoder = new TextEncoder();
  const data = report
    ? `event: REPORT_READY\ndata: ${JSON.stringify({ type: 'REPORT_READY', payload: { report } })}\n\n`
    : 'event: PLANNING_STARTED\ndata: {"type":"PLANNING_STARTED","payload":{"message":"Working"}}\n\n';
  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(data));
      controller.close();
    }
  });
}

describe('AnalysisSessionWorkspace API and demo states', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('labels explicit event fixtures as simulation and does not open a mock report artifact', () => {
    const viewModel = projectAnalysisSession(mockCompanyOnlyEvents);
    render(<AnalysisSessionWorkspace viewModel={viewModel} />);

    expect(screen.getByText('Mô phỏng · dữ liệu minh họa')).toBeInTheDocument();
    expect(screen.getByText('Kịch bản mô phỏng đã kết thúc')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Xem báo cáo phân tích/ })).not.toBeInTheDocument();
  });

  it('opens only the report artifact returned by the live API and preserves partial status', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body: reportStream({ report_id: 'rep-live', status: 'partial' })
    } as unknown as Response);

    render(
      <MemoryRouter>
        <AnalysisSessionWorkspace
          isLiveStream
          streamRequest={{ query: 'Phân tích ROE của ACB', target_ticker: 'ACB', period: '2024_Q4' }}
        />
      </MemoryRouter>
    );

    expect(await screen.findByRole('button', { name: /Xem báo cáo phân tích/ })).toBeInTheDocument();
    expect(screen.getByText('API đã trả về phản hồi')).toBeInTheDocument();
    expect(screen.getByText('partial')).toBeInTheDocument();
    expect(screen.queryByText('Mô phỏng · dữ liệu minh họa')).not.toBeInTheDocument();
  });

  it('reports API failure without substituting demo events or report data', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'));

    render(
      <MemoryRouter>
        <AnalysisSessionWorkspace
          isLiveStream
          streamRequest={{ query: 'Phân tích ROE của ACB', target_ticker: 'ACB', period: '2024_Q4' }}
        />
      </MemoryRouter>
    );

    expect(await screen.findByText(/Lỗi kết nối Live SSE/)).toBeInTheDocument();
    expect(screen.getByText('API lỗi')).toBeInTheDocument();
    expect(screen.queryByText('Mô phỏng · dữ liệu minh họa')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Xem báo cáo phân tích/ })).not.toBeInTheDocument();
  });

  it('does not present a report action when a stream ends without REPORT_READY', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      body: reportStream()
    } as unknown as Response);

    render(
      <MemoryRouter>
        <AnalysisSessionWorkspace
          isLiveStream
          streamRequest={{ query: 'Phân tích ROE của ACB', target_ticker: 'ACB', period: '2024_Q4' }}
        />
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText('API lỗi')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /Xem báo cáo phân tích/ })).not.toBeInTheDocument();
  });
});
