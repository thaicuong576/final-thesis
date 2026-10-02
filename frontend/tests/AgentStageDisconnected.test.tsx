import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AgentStage } from '../src/features/analysis-session/components/AgentStage';
import type { TraceStep } from '../src/features/analysis-session/model/types';

describe('AgentStage disconnected state (UPFIX-1 Bug 3)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const mockSteps: TraceStep[] = [
    {
      step_id: 'step-1',
      seq: 1,
      t_ms: 13000,
      actor: 'orchestrator',
      recipient: null,
      kind: 'plan',
      summary: 'Dựng kế hoạch phân tích',
      detail: {
        question_type: 'company_profile',
        agents: [{ agent: 'company', decision: 'run', reason: 'Cần phân tích chỉ tiêu' }],
      },
    },
  ];

  it('shows "Các tác tử đang làm việc" and increments timer while live and connected', () => {
    render(
      <AgentStage
        steps={mockSteps}
        query="Phân tích ROE của VPB"
        live={true}
        isDisconnected={false}
      />
    );

    expect(screen.getByText('Các tác tử đang làm việc')).toBeInTheDocument();
    expect(screen.queryByText('Mất kết nối')).not.toBeInTheDocument();

    // Advance 200ms so initial step is revealed by step animation
    act(() => {
      vi.advanceTimersByTime(200);
    });

    // Elapsed formatted (13s -> 0:13)
    expect(screen.getByLabelText('Thời gian đã chạy')).toHaveTextContent('0:13');

    // Advance 3 seconds
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.getByText('Các tác tử đang làm việc')).toBeInTheDocument();
  });

  it('stops timer and replaces header status text with "Mất kết nối" when disconnected', () => {
    const onRetry = vi.fn();

    const { rerender } = render(
      <AgentStage
        steps={mockSteps}
        query="Phân tích ROE của VPB"
        live={true}
        isDisconnected={false}
        onRetry={onRetry}
      />
    );

    // Let the live timer advance past step revelation
    act(() => {
      vi.advanceTimersByTime(15000);
    });

    // Disconnect happens
    rerender(
      <AgentStage
        steps={mockSteps}
        query="Phân tích ROE của VPB"
        live={true}
        isDisconnected={true}
        onRetry={onRetry}
      />
    );

    // Header status text MUST be "Mất kết nối"
    expect(screen.getByText('Mất kết nối')).toBeInTheDocument();
    expect(screen.queryByText('Các tác tử đang làm việc')).not.toBeInTheDocument();

    // Footer shows disconnect notification and retry button
    expect(screen.getByText('Mất kết nối. Thử lại')).toBeInTheDocument();

    const timeAtDisconnect = screen.getByLabelText('Thời gian đã chạy').textContent;

    // Advance timer by 20 minutes (1200 seconds) - as reported in Bug 3
    act(() => {
      vi.advanceTimersByTime(1200000);
    });

    // Time MUST NOT have run on to 20:07! It must remain frozen!
    const timeAfterAdvance = screen.getByLabelText('Thời gian đã chạy').textContent;
    expect(timeAfterAdvance).toBe(timeAtDisconnect);

    // When user presses "Thử lại"
    const retryBtn = screen.getByRole('button', { name: /Thử lại/i });
    fireEvent.click(retryBtn);
    expect(onRetry).toHaveBeenCalledTimes(1);

    // Stream re-establishes connection
    rerender(
      <AgentStage
        steps={mockSteps}
        query="Phân tích ROE của VPB"
        live={true}
        isDisconnected={false}
        onRetry={onRetry}
      />
    );

    // Normal state resumes
    expect(screen.getByText('Các tác tử đang làm việc')).toBeInTheDocument();
    expect(screen.queryByText('Mất kết nối')).not.toBeInTheDocument();
  });
});
