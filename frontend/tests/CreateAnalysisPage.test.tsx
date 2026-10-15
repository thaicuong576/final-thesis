import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CreateAnalysisPage } from '../src/pages/create-analysis/CreateAnalysisPage';
import { capabilityService } from '../src/entities/capability/api/capabilityService';
import type { AnalysisCapabilities } from '../src/entities/capability/model/types';
import traceFixture from '../src/test/fixtures/er-trace-acb-2024q4.json';
import type { TraceStep } from '../src/features/analysis-session/model/types';

function mockCapabilities(overrides: Partial<AnalysisCapabilities> = {}): AnalysisCapabilities {
  return {
    analysis_available: true,
    implemented_capabilities: ['company', 'sector'],
    dataset_snapshot_id: 'snapshot-2024q4',
    entities: [
      { id: 'ACB', ticker: 'ACB', name: 'Ngân hàng Á Châu' },
      { id: 'MBB', ticker: 'MBB', name: 'Ngân hàng Quân đội' },
      { id: 'TCB', ticker: 'TCB', name: 'Techcombank' },
      { id: 'VCB', ticker: 'VCB', name: 'Vietcombank' },
      { id: 'VPB', ticker: 'VPB', name: 'VPBank' }
    ],
    periods: [
      { id: '2024_Q1', quarter: 1, year: 2024 },
      { id: '2024_Q2', quarter: 2, year: 2024 },
      { id: '2024_Q3', quarter: 3, year: 2024 },
      { id: '2024_Q4', quarter: 4, year: 2024 }
    ],
    metrics: [
      { id: 'bank.npl_g35', topicId: 'camels', acronym: 'NPL_G35', label: 'Tỷ lệ nợ xấu', shortLabel: 'Nợ xấu', unit: '%', direction: 'lower_is_better', decimals: 2, group: 'asset_quality', groupLabel: 'Chất lượng nợ' },
      { id: 'bank.llr_coverage', topicId: 'camels', acronym: 'LLR', label: 'Bao phủ nợ xấu', shortLabel: 'Bao phủ', unit: '%', direction: 'higher_is_better', decimals: 1, group: 'provisioning', groupLabel: 'Đệm dự phòng' },
      { id: 'bank.roa', topicId: 'camels', acronym: 'ROA', label: 'ROA', shortLabel: 'ROA', unit: '%', direction: 'higher_is_better', decimals: 2, group: 'profitability', groupLabel: 'Sinh lời' },
      { id: 'bank.roe', topicId: 'camels', acronym: 'ROE', label: 'ROE', shortLabel: 'ROE', unit: '%', direction: 'higher_is_better', decimals: 1, group: 'profitability', groupLabel: 'Sinh lời' }
    ],
    suggestedQuestions: [
      'Sinh lời của MBB thay đổi thế nào trong năm 2024?',
      'Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu?'
    ],
    topics: [],
    macro: {
      status: 'AVAILABLE',
      minimumContractSatisfied: true,
      summary: '',
      details: ''
    },
    ...overrides
  };
}

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

function renderAskPage(initialMode: 'ASK' | 'SESSION' = 'ASK', initialSteps?: TraceStep[]) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={['/analysis']}>
      <QueryClientProvider client={client}>
        <CreateAnalysisPage initialMode={initialMode} initialSteps={initialSteps} />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

describe('ER-6 AskPage (Lean Ask Screen)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(capabilityService, 'getCapabilities').mockResolvedValue(mockCapabilities());
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/runs')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              run_id: 'run-1',
              query: 'Sức khỏe tài chính của ACB so với các ngân hàng cùng nhóm, quý 4/2024',
              created_at: '2024-12-31T17:00:00Z',
              status: 'completed'
            }
          ]
        } as Response);
      }
      if (url.includes('/api/analyze/stream')) {
        const stream = createMockStream([
          `event: TRACE_STEP\ndata: ${JSON.stringify({
            step_id: 't-1',
            seq: 1,
            t_ms: 100,
            actor: 'orchestrator',
            kind: 'plan',
            summary: 'Lập kế hoạch phân tích',
            detail: { question_type: 'company_profile' }
          })}\n\n`
        ]);
        return Promise.resolve({
          ok: true,
          status: 200,
          body: stream
        } as unknown as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({})
      } as Response);
    });
  });

  it('renders the lean ask screen without chips, snapshot IDs, or "API: ..." labels', async () => {
    renderAskPage();

    // 1. Page title
    expect(await screen.findByText('Bạn muốn phân tích gì?')).toBeInTheDocument();

    // 2. Textarea and analyze button
    const textarea = screen.getByRole('textbox', { name: 'Câu hỏi phân tích' });
    expect(textarea).toBeInTheDocument();
    const analyzeBtn = screen.getByRole('button', { name: /Phân tích/i });
    expect(analyzeBtn).toBeInTheDocument();
    // High-contrast text token on dark background
    expect(analyzeBtn.className).toContain('bg-ink');
    expect(analyzeBtn.className).toMatch(/text-(ink-inverse|\[var\(--text-inverse\)\]|text-inverse)/);

    // 3. Availability summary line
    expect(screen.getByText(/Dữ liệu hiện có: ACB, MBB, TCB, VCB, VPB · Q1–Q4\/2024 · Nợ xấu, Bao phủ, ROA, ROE/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Chi tiết' })).toHaveAttribute('href', '/data');

    // 4. Must NOT have chips, snapshot IDs, or API labels
    expect(screen.queryByText(/Snapshot đã kiểm định/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Phạm vi dữ liệu API công bố/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/snapshot-2024q4/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Mẫu minh họa/i)).not.toBeInTheDocument();
  });

  it('renders analyze button with valid high-contrast text color token', async () => {
    renderAskPage();
    const analyzeBtn = await screen.findByRole('button', { name: /Phân tích/i });
    expect(analyzeBtn).toBeInTheDocument();
    expect(analyzeBtn.className).toContain('bg-ink');
    expect(analyzeBtn.className).toMatch(/text-(ink-inverse|\[var\(--text-inverse\)\]|text-inverse)/);
  });

  it('renders backend suggested questions and populates textarea on click without submitting', async () => {
    const user = userEvent.setup();
    renderAskPage();

    expect(await screen.findByText('Thử hỏi')).toBeInTheDocument();
    const suggestionBtn = screen.getByRole('button', { name: 'Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu?' });
    expect(suggestionBtn).toBeInTheDocument();

    // Click suggestion
    await user.click(suggestionBtn);

    // Fills textarea
    const textarea = screen.getByRole('textbox', { name: 'Câu hỏi phân tích' });
    expect(textarea).toHaveValue('Tỷ lệ nợ xấu của VCB quý 4/2024 là bao nhiêu?');

    // Does not auto-submit (remains on Ask page)
    expect(screen.getByText('Bạn muốn phân tích gì?')).toBeInTheDocument();
  });

  it('submits request with query when clicking Phân tích button', async () => {
    const user = userEvent.setup();
    renderAskPage();

    const textarea = await screen.findByRole('textbox', { name: 'Câu hỏi phân tích' });
    await user.type(textarea, 'So sánh ACB và TCB quý 4/2024');

    const submitBtn = screen.getByRole('button', { name: /Phân tích/i });
    await user.click(submitBtn);

    // Switches to session workspace
    expect(await screen.findByRole('region', { name: 'Điều phối viên' })).toBeInTheDocument();
  });

  it('renders session workspace with fixture steps when requested', async () => {
    const steps = traceFixture.steps as unknown as TraceStep[];
    renderAskPage('SESSION', steps);

    expect(await screen.findByRole('region', { name: 'Điều phối viên' })).toBeInTheDocument();
    expect(screen.getByRole('log')).toBeInTheDocument();
  });

  it('handles legacy RUN_BLOCKED by returning to ask screen with error banner and preserved query', async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/api/runs')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => []
        } as Response);
      }
      if (url.includes('/api/analyze/stream')) {
        const stream = createMockStream([
          `event: RUN_BLOCKED\ndata: ${JSON.stringify({
            status: 'error',
            reason: 'unsupported_period',
            error: {
              code: 'unsupported_period',
              message: 'Giai đoạn phân tích chưa được hỗ trợ.',
              suggestions: ['Thử quý 4/2024']
            }
          })}\n\n`
        ]);
        return Promise.resolve({
          ok: true,
          status: 200,
          body: stream
        } as unknown as Response);
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response);
    });

    renderAskPage();

    const textarea = await screen.findByRole('textbox', { name: 'Câu hỏi phân tích' });
    await user.type(textarea, 'Tăng trưởng tín dụng quý 2/2020');

    const submitBtn = screen.getByRole('button', { name: /Phân tích/i });
    await user.click(submitBtn);

    // Should return to Ask screen, preserving user query and showing error banner
    expect(await screen.findByText('Kỳ bạn hỏi chưa có trong dữ liệu. Dữ liệu hiện có: Q1–Q4/2024.')).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Câu hỏi phân tích' })).toHaveValue('Tăng trưởng tín dụng quý 2/2020');
    expect(screen.getByRole('button', { name: /Thử quý 4\/2024/i })).toBeInTheDocument();
  });
});
