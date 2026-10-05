import { render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { dedupeRunTickers } from '../src/pages/reports/reportTickers';
import { ReportsListPage } from '../src/pages/reports/ReportsListPage';

describe('dedupeRunTickers', () => {
  it('deduplicates target and peers preserving target first then peer order', () => {
    expect(dedupeRunTickers('ACB', ['ACB', 'TCB'])).toEqual(['ACB', 'TCB']);
  });

  it('keeps distinct target and peers in order', () => {
    expect(dedupeRunTickers('ACB', ['TCB', 'VCB'])).toEqual(['ACB', 'TCB', 'VCB']);
  });

  it('handles null target and deduplicates duplicate peers', () => {
    expect(dedupeRunTickers(null, ['TCB', 'TCB'])).toEqual(['TCB']);
  });

  it('handles undefined peers when target is present', () => {
    expect(dedupeRunTickers('ACB', undefined)).toEqual(['ACB']);
  });

  it('ignores case and surrounding whitespace, returning one tag with first occurrence text', () => {
    const result = dedupeRunTickers(' acb ', ['ACB']);
    expect(result).toHaveLength(1);
    expect(result).toEqual([' acb ']);
  });

  it('does not crash and ignores empty or whitespace-only tickers', () => {
    expect(dedupeRunTickers('', ['  ', '\t', 'VCB'])).toEqual(['VCB']);
    expect(dedupeRunTickers(undefined, null)).toEqual([]);
  });
});

describe('ReportsListPage bank tags render', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders exactly one bank tag per ticker for a head-to-head run', async () => {
    const runs = [
      {
        run_id: 'run-h2h-1',
        created_at: '2026-10-01T02:00:00Z',
        query: 'So sánh ACB và TCB quý 4/2024',
        target_ticker: 'ACB',
        peer_tickers: ['ACB', 'TCB'],
        period: '2024_Q4',
        status: 'completed',
        question_type: 'head_to_head',
        duration_ms: 12000
      }
    ];

    const fetchMock = vi.fn<(input: RequestInfo | URL) => Promise<Response>>(async () =>
      new Response(JSON.stringify(runs), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      })
    );
    vi.stubGlobal('fetch', fetchMock);

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/reports']}>
          <Routes>
            <Route path="/reports" element={<ReportsListPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    const rowHeader = await screen.findByText('So sánh ACB và TCB quý 4/2024');
    const row = rowHeader.closest('li')!;
    expect(row).toBeInTheDocument();

    const acbTags = within(row).getAllByText('ACB');
    expect(acbTags).toHaveLength(1);

    const tcbTags = within(row).getAllByText('TCB');
    expect(tcbTags).toHaveLength(1);
  });
});
