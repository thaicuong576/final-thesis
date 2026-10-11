import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { RankHeatmap } from '../src/features/equity-report/charts/RankHeatmap';
import { SourceNotes } from '../src/features/equity-report/components/SourceNotes';
import { EquityReportProvider } from '../src/features/equity-report/components/EquityReportContext';
import { AdaptiveReport } from '../src/features/equity-report/components/AdaptiveReport';
import type { AdaptiveReportResponse, Dataset, ReportBlock, Sentence, SourceNote } from '../src/features/equity-report';

import t01Run from '../../experiments/er9/runs/er9-T01-hierarchical_with_critique-r0.json';
import t07Run from '../../experiments/er9/runs/er9-T07-hierarchical_with_critique-r0.json';

const t01Response = t01Run.response as unknown as AdaptiveReportResponse;
const t07Response = t07Run.response as unknown as AdaptiveReportResponse;

describe('Report Visual Layout Invariants (Task RPT-1)', () => {
  it('pivot from a 40-row peer dataset gives 10 rows × 4 columns plus a median row', () => {
    // Dataset 0 in T01 is a 40-row peer_table (10 banks x 4 metrics)
    const datasets = t01Response.datasets ?? [];
    const peerDataset = datasets[0] as Dataset;
    expect(peerDataset.rows).toHaveLength(40);
    expect(peerDataset.shape).toBe('peer_table');

    const { container } = render(
      <RankHeatmap
        dataset={peerDataset}
        metrics={[]}
        highlight={['BID']}
      />
    );

    // Header has Ngân hàng + 4 metric columns = 5 th elements
    const ths = container.querySelectorAll('thead th');
    expect(ths).toHaveLength(5);

    // Initially collapsed: shows toggle with total 10 banks
    const toggleBtn = screen.getByRole('button', { name: /Xem đủ 10 ngân hàng/i });
    expect(toggleBtn).toBeInTheDocument();

    // Click toggle to expand all banks
    fireEvent.click(toggleBtn);

    // 10 bank rows + 1 median row = 11 tr elements in tbody
    const tbodyRows = container.querySelectorAll('tbody tr');
    expect(tbodyRows).toHaveLength(11);

    // Median row exists at the bottom
    expect(screen.getByText('Trung vị')).toBeInTheDocument();

    // Focal bank BID has highlight styling
    expect(screen.getByText('BID')).toBeInTheDocument();
    expect(screen.getByText('Mục tiêu')).toBeInTheDocument();
  });

  it('missing cell shows its reason, not 0', () => {
    const missingDataset: Dataset = {
      dataset_id: 'test-missing-ds',
      shape: 'peer_table',
      title: 'Ma trận thử nghiệm khuyết thiếu',
      produced_by: { tool: 'peer_position', agent: 'specialist' },
      metric_ids: ['bank.npl_g35', 'bank.roa'],
      periods: ['2026_Q2'],
      highlight_entity_ids: ['BID'],
      reference_lines: [],
      allowed_charts: ['rank_heatmap'],
      rows: [
        {
          entity_id: 'ACB',
          metric_id: 'bank.npl_g35',
          period: '2026_Q2',
          value: null,
          status: 'missing',
          observation_id: null,
          rank_better: null,
          rank_desc: null,
          missing_reason: 'Chưa công bố BCTC Q2'
        },
        {
          entity_id: 'ACB',
          metric_id: 'bank.roa',
          period: '2026_Q2',
          value: 2.1,
          status: 'valid',
          observation_id: 'obs-acb-roa',
          rank_better: 1,
          rank_desc: 1,
          missing_reason: null
        },
        {
          entity_id: 'BID',
          metric_id: 'bank.npl_g35',
          period: '2026_Q2',
          value: 1.5,
          status: 'valid',
          observation_id: 'obs-bid-npl',
          rank_better: 1,
          rank_desc: 1,
          missing_reason: null
        },
        {
          entity_id: 'BID',
          metric_id: 'bank.roa',
          period: '2026_Q2',
          value: 1.8,
          status: 'valid',
          observation_id: 'obs-bid-roa',
          rank_better: 2,
          rank_desc: 2,
          missing_reason: null
        }
      ]
    };

    const { container } = render(
      <RankHeatmap
        dataset={missingDataset}
        metrics={[]}
        highlight={['BID']}
      />
    );

    // Missing reason must be visible
    expect(screen.getByText('Chưa công bố BCTC Q2')).toBeInTheDocument();

    // Cell displays "—" for missing, not 0 or 0%
    const cells = container.querySelectorAll('tbody td');
    const cellTexts = Array.from(cells).map((c) => c.textContent);
    
    // Check that none of the cells equal '0', '0%', or '0,0%'
    expect(cellTexts).not.toContain('0');
    expect(cellTexts).not.toContain('0%');
    expect(cellTexts).not.toContain('0,0%');
    expect(cellTexts).not.toContain('0,00%');
    // Em dash is present for the missing cell
    expect(cellTexts.some((txt) => txt?.includes('—'))).toBe(true);
  });

  it('grouped source list has one entry per filing', () => {
    // 1. Synthetic test matching TASK.md: 40 source notes spanning 10 bank filings (4 metrics each)
    const banks = ['ACB', 'BID', 'CTG', 'HDB', 'MBB', 'SHB', 'STB', 'TCB', 'VCB', 'VPB'];
    const syntheticNotes: SourceNote[] = [];
    let noteCounter = 1;
    banks.forEach((b) => {
      for (let m = 1; m <= 4; m++) {
        syntheticNotes.push({
          note_no: noteCounter++,
          source_id: `src-${b}-${m}`,
          title: `${b} · Báo cáo tài chính Hợp nhất Q2/2026`,
          url: `https://example.com/${b}.pdf`,
          locator: `pdf_pages:${10 + m}`,
          fact_ids: []
        });
      }
    });

    const mockReport40: AdaptiveReportResponse = {
      ...t01Response,
      source_notes: syntheticNotes
    };

    const { container: container40 } = render(
      <EquityReportProvider report={mockReport40}>
        <SourceNotes />
      </EquityReportProvider>
    );

    // Summary heading shows 10 filings, 40 data points
    expect(screen.getByText(/Nguồn: 10 báo cáo tài chính, 40 số liệu/i)).toBeInTheDocument();

    // ol contains exactly 10 li elements (one per bank filing)
    const filingItems40 = container40.querySelectorAll('#source-notes ol li');
    expect(filingItems40).toHaveLength(10);

    // Each note_no is still accessible in the DOM
    for (let i = 1; i <= 40; i++) {
      expect(container40.querySelector(`#note-${i}`)).not.toBeNull();
    }

    // 2. Real fixture T01: 21 notes grouped by 11 filings
    const { container: containerT01 } = render(
      <EquityReportProvider report={t01Response}>
        <SourceNotes />
      </EquityReportProvider>
    );
    expect(screen.getByText(/Nguồn: 11 báo cáo tài chính, 21 số liệu/i)).toBeInTheDocument();
    const filingItemsT01 = containerT01.querySelectorAll('#source-notes ol li');
    expect(filingItemsT01).toHaveLength(11);
  });

  it('section + figure render in the same unit', () => {
    const { container } = render(
      <MemoryRouter>
        <AdaptiveReport report={t01Response} />
      </MemoryRouter>
    );

    // Units paired as section_figure must have data-testid="section-figure-unit"
    const units = container.querySelectorAll('[data-testid="section-figure-unit"]');
    expect(units.length).toBeGreaterThanOrEqual(1);

    // In T01, the first section_figure unit contains both section text and chart figure
    const firstUnit = units[0];
    expect(firstUnit.querySelector('p')).not.toBeNull(); // section paragraph
    expect(firstUnit.querySelector('figure') || firstUnit.querySelector('table')).not.toBeNull(); // chart/table
  });

  it('no sentence lost (count sentences in report_spec vs rendered)', () => {
    // Helper to recursively collect all sentences from report_spec blocks
    function collectSentences(blocks: ReportBlock[]): Sentence[] {
      const result: Sentence[] = [];
      for (const b of blocks) {
        if ('sentence' in b && b.sentence) {
          result.push(b.sentence);
        }
        if ('sentences' in b && Array.isArray(b.sentences)) {
          result.push(...b.sentences);
        }
        if ('blocks' in b && Array.isArray(b.blocks)) {
          result.push(...collectSentences(b.blocks as ReportBlock[]));
        }
      }
      return result;
    }

    const t07Blocks = t07Response.report_spec?.blocks ?? [];
    const expectedSentences = collectSentences(t07Blocks);
    expect(expectedSentences.length).toBeGreaterThan(0);

    const { container } = render(
      <MemoryRouter>
        <AdaptiveReport report={t07Response} />
      </MemoryRouter>
    );

    const fullRenderedText = container.textContent || '';

    // Verify every sentence's text appears in the rendered output
    for (const sent of expectedSentences) {
      // First 25 characters of each sentence to avoid whitespace/punctuation formatting differences
      const sample = sent.text.slice(0, 25).trim();
      expect(fullRenderedText).toContain(sample);
    }
  });
});
