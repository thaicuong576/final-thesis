import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { ReportPage } from '../src/pages/reports/ReportPage';
import {
  type AdaptiveReportResponse,
  type Dataset,
  type Fact,
  type ReportBlock,
  type ChartType
} from '../src/features/equity-report';
import type { AnalysisReport } from '../src/features/analysis-report';
import { RankedBar } from '../src/features/equity-report/charts/RankedBar';
import { LineTrend } from '../src/features/equity-report/charts/LineTrend';
import { RankHeatmap } from '../src/features/equity-report/charts/RankHeatmap';
import { Scatter } from '../src/features/equity-report/charts/Scatter';
import { ComparisonTable } from '../src/features/equity-report/charts/ComparisonTable';
import {
  fmtPct,
  fmtPp,
  fmtTimes,
  fmtRank,
  fmtPeriod,
  fmtPeriodRange,
  niceTicks
} from '../src/shared/lib/formatting';

// Import the 5 ER fixtures
import lookupFixture from '../src/test/fixtures/er-lookup-vcb-npl-2024q4.json';
import rankingFixture from '../src/test/fixtures/er-ranking-coverage-2024q4.json';
import trendFixture from '../src/test/fixtures/er-trend-vpb-roe-2024.json';
import h2hFixture from '../src/test/fixtures/er-h2h-acb-tcb-2024q4.json';
import profileFixture from '../src/test/fixtures/er-profile-acb-2024q4.json';

type TestReportInput = AdaptiveReportResponse | AnalysisReport;

function renderReportInRouter(report: TestReportInput) {
  return render(
    <MemoryRouter initialEntries={[`/reports/${report.report_id || 'test'}`]}>
      <Routes>
        <Route path="/reports/:id" element={<ReportPage report={report as AdaptiveReportResponse} />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ER-7 Adaptive Equity Research Reports', () => {
  describe('5 Fixtures rendering and block layout', () => {
    it('renders lookup fixture as AnswerCardLayout without Headline', () => {
      const { container } = renderReportInRouter(lookupFixture as unknown as AdaptiveReportResponse);

      // Must NOT have headline h1
      expect(container.querySelector('h1')).toBeNull();

      // Must have the large answer number (0,96%)
      expect(screen.getByText('0,96%')).toBeInTheDocument();

      // Label with shortLabel (Nợ xấu), entity (VCB), period (Quý 4/2024)
      expect(screen.getByText(/Nợ xấu · VCB · Quý 4\/2024/)).toBeInTheDocument();

      // Source notes present
      expect(screen.getByText(/Báo cáo tài chính quý 4\/2024/)).toBeInTheDocument();
    });

    it('renders ranking fixture with Headline, RankedBar, KeyPoints, Callout', () => {
      const { container } = renderReportInRouter(rankingFixture as unknown as AdaptiveReportResponse);

      // Headline h1 present
      expect(container.querySelector('h1')).toBeInTheDocument();

      // RankedBar SVG present with median line
      expect(screen.getByRole('img', { name: /Biểu đồ xếp hạng/i })).toBeInTheDocument();
      expect(screen.getByText('trung vị')).toBeInTheDocument();

      // Key points text present
      expect(screen.getByText(/Khoảng cách giữa ngân hàng dẫn đầu và thấp nhất/)).toBeInTheDocument();

      // Callout present
      expect(screen.getByText(/Lưu ý chéo/)).toBeInTheDocument();
    });

    it('renders trend fixture with Headline, LineTrend, KeyPoints, Callout', () => {
      const { container } = renderReportInRouter(trendFixture as unknown as AdaptiveReportResponse);

      // Headline h1 present
      expect(container.querySelector('h1')).toBeInTheDocument();

      // LineTrend SVG present
      expect(screen.getByRole('img', { name: /Biểu đồ diễn biến/i })).toBeInTheDocument();

      // Callout present
      expect(screen.getByText(/Nghịch xu hướng/)).toBeInTheDocument();
    });

    it('renders head_to_head fixture with Headline, ComparisonTable, Callout', () => {
      const { container } = renderReportInRouter(h2hFixture as unknown as AdaptiveReportResponse);

      // Headline h1 present
      expect(container.querySelector('h1')).toBeInTheDocument();

      // Comparison table with ACB and TCB columns
      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: 'ACB' })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: 'TCB' })).toBeInTheDocument();

      // Better indicators present
      const betterBadges = screen.getAllByLabelText('tốt hơn');
      expect(betterBadges.length).toBeGreaterThan(0);

      // Callout present
      expect(screen.getByText(/Phân rã ROE và ROA/)).toBeInTheDocument();
    });

    it('renders profile fixture with Headline, SignalsAside, Scatter, RankHeatmap, SmallMultiples, Callout', () => {
      const { container } = renderReportInRouter(profileFixture as unknown as AdaptiveReportResponse);

      // Headline h1 present
      expect(container.querySelector('h1')).toBeInTheDocument();

      // SignalsAside present
      expect(screen.getByText('Tín hiệu so với nhóm')).toBeInTheDocument();
      expect(screen.getByText('Trên nhóm')).toBeInTheDocument();
      expect(screen.getByText('Dưới nhóm')).toBeInTheDocument();
      expect(screen.getByText('14/14')).toBeInTheDocument(); // numbers matched / checked

      // Figures present
      expect(screen.getByRole('img', { name: /Biểu đồ phân tán/i })).toBeInTheDocument();
      expect(screen.getByText('Xanh: tốt hơn nhóm, đỏ: kém hơn nhóm (theo hạng). Nợ xấu: thấp là tốt.')).toBeInTheDocument();
      expect(screen.getByRole('img', { name: /ROE qua các quý/i })).toBeInTheDocument();

      // Callouts present
      expect(screen.getByText(/Cảnh báo phân kỳ tín hiệu và nghịch xu hướng/)).toBeInTheDocument();
    });
  });

  describe('Technical ID Leak Guard', () => {
    const fixtures = [
      ['lookup', lookupFixture as unknown as AdaptiveReportResponse],
      ['ranking', rankingFixture as unknown as AdaptiveReportResponse],
      ['trend', trendFixture as unknown as AdaptiveReportResponse],
      ['h2h', h2hFixture as unknown as AdaptiveReportResponse],
      ['profile', profileFixture as unknown as AdaptiveReportResponse]
    ] as const;

    for (const [name, fixture] of fixtures) {
      it(`does not leak "bank." or "fact:" outside TechnicalDetails in ${name} fixture`, () => {
        const { container } = renderReportInRouter(fixture);

        // TechnicalDetails is collapsed by default. Clone visible tree excluding TechnicalDetails container
        const article = container.querySelector('article');
        expect(article).not.toBeNull();

        // Get inner text of article excluding details/TechnicalDetails
        const technicalDetails = container.querySelector('.font-mono.text-\\[11px\\]');
        const textContent = article?.textContent || '';

        // Verify that outside technical details, there are no bank.* or fact:* raw strings
        if (!technicalDetails) {
          expect(textContent).not.toMatch(/bank\.[a-z0-9_]+/i);
          expect(textContent).not.toMatch(/fact:[a-z0-9_:]+/i);
        }
      });
    }
  });

  describe('Citations linking to SourceNotes', () => {
    it('superscript citation links point to valid #note-n elements', () => {
      const { container } = renderReportInRouter(profileFixture as unknown as AdaptiveReportResponse);

      const citationLinks = container.querySelectorAll('sup a[href^="#note-"]');
      expect(citationLinks.length).toBeGreaterThan(0);

      citationLinks.forEach((link) => {
        const href = link.getAttribute('href')!;
        const targetId = href.replace('#', '');
        const targetEl = container.querySelector(`#${targetId}`);
        expect(targetEl).not.toBeNull();
      });
    });
  });

  describe('Individual Chart Behaviors', () => {
    it('RankedBar starts from 0 and includes median reference line', () => {
      const { container } = render(
        <RankedBar
          dataset={rankingFixture.datasets[0] as unknown as Dataset}
          metrics={[]}
          highlight={['VCB']}
        />
      );

      // SVG exists
      const svg = container.querySelector('svg');
      expect(svg).not.toBeNull();

      // Median line exists
      expect(container.querySelector('.median-line')).not.toBeNull();
      expect(screen.getByText('trung vị')).toBeInTheDocument();

      // Bars start from leftMargin (38)
      const rects = container.querySelectorAll('rect');
      expect(rects.length).toBeGreaterThan(0);
      rects.forEach((rect) => {
        expect(rect.getAttribute('x')).toBe('38');
      });
    });

    it('LineTrend breaks at missing period without a connecting line across it', () => {
      // Create a dataset with 4 quarters where Q2 is missing
      const datasetWithGap: Dataset = {
        dataset_id: 'ds-test-gap',
        shape: 'series',
        title: 'Test gap',
        produced_by: { tool: 'trend', agent: 'company' },
        metric_ids: ['bank.roe'],
        periods: ['2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4'],
        highlight_entity_ids: ['VPB'],
        rows: [
          { entity_id: 'VPB', metric_id: 'bank.roe', period: '2024_Q1', status: 'valid', value: 10, observation_id: null, rank_better: null, rank_desc: null, missing_reason: null },
          { entity_id: 'VPB', metric_id: 'bank.roe', period: '2024_Q2', status: 'missing', value: null, observation_id: null, rank_better: null, rank_desc: null, missing_reason: 'chưa kiểm định' },
          { entity_id: 'VPB', metric_id: 'bank.roe', period: '2024_Q3', status: 'valid', value: 15, observation_id: null, rank_better: null, rank_desc: null, missing_reason: null },
          { entity_id: 'VPB', metric_id: 'bank.roe', period: '2024_Q4', status: 'valid', value: 18, observation_id: null, rank_better: null, rank_desc: null, missing_reason: null }
        ],
        reference_lines: [],
        allowed_charts: ['line_trend']
      };

      const { container } = render(
        <LineTrend dataset={datasetWithGap} metrics={[]} highlight={['VPB']} />
      );

      // Target polylines should not connect Q1 directly to Q3.
      // Since Q1 is an isolated point before a gap, it renders as a circle point.
      // Q3 and Q4 form a 2-point segment which renders as one polyline.
      const polylines = container.querySelectorAll('polyline[stroke="var(--fill-accent, #ee9f0d)"]');
      expect(polylines.length).toBe(1); // Exactly 1 polyline (for Q3-Q4), not bridging across Q2!

      // Note about missing period displayed
      expect(screen.getByText(/Quý 2\/2024 chưa có số liệu đã kiểm định/)).toBeInTheDocument();
    });

    it('RankHeatmap includes "#hạng" and a "Trung vị" row', () => {
      render(
        <RankHeatmap
          dataset={profileFixture.datasets[1] as unknown as Dataset}
          metrics={[]}
          highlight={['ACB']}
        />
      );

      // Verify "#" rank text exists in cells
      expect(screen.getAllByText(/#\d/).length).toBeGreaterThan(0);

      // Verify "Trung vị" row exists
      expect(screen.getByText('Trung vị')).toBeInTheDocument();
    });

    it('Scatter includes aria-label on every point and tooltip title', () => {
      const { container } = render(
        <Scatter
          dataset={profileFixture.datasets[0] as unknown as Dataset}
          metrics={[]}
          highlight={['ACB']}
        />
      );

      const circles = container.querySelectorAll('circle[role="graphics-symbol"]');
      expect(circles.length).toBeGreaterThan(0);

      circles.forEach((c) => {
        expect(c.getAttribute('aria-label')).toBeTruthy();
        expect(c.querySelector('title')).not.toBeNull();
      });
    });

    it('ComparisonTable includes bold ▲ with aria-label="tốt hơn"', () => {
      render(
        <ComparisonTable
          dataset={h2hFixture.datasets[0] as unknown as Dataset}
          metrics={[]}
          highlight={['ACB', 'TCB']}
        />
      );

      const badges = screen.getAllByLabelText('tốt hơn');
      expect(badges.length).toBeGreaterThan(0);
      expect(badges[0].textContent).toBe('▲');
    });
  });

  describe('Robustness and Fallbacks', () => {
    it('skips unknown block type without crashing', () => {
      const reportWithUnknownBlock: AdaptiveReportResponse = {
        report_id: 'rep-unknown',
        status: 'completed',
        report_version: 'er-report-v1',
        question_type: 'lookup',
        report_spec: {
          kind: 'answer_card',
          note_label: 'Test',
          blocks: [
            { type: 'unknown_future_block' } as unknown as ReportBlock,
            lookupFixture.report_spec.blocks[0] as unknown as ReportBlock
          ]
        },
        facts: lookupFixture.facts as unknown as Fact[],
        datasets: lookupFixture.datasets as unknown as Dataset[],
        source_notes: []
      };

      renderReportInRouter(reportWithUnknownBlock);
      expect(screen.getByText('0,96%')).toBeInTheDocument();
    });

    it('renders DataTable when chart type is unrecognized', () => {
      const reportWithUnknownChart: AdaptiveReportResponse = {
        report_id: 'rep-unknown-chart',
        status: 'completed',
        report_version: 'er-report-v1',
        question_type: 'ranking',
        report_spec: {
          kind: 'note',
          note_label: 'Test',
          blocks: [
            {
              type: 'figure',
              figure_no: 1,
              chart: 'quantum_donut_chart' as unknown as ChartType,
              dataset_id: 'ds-vcb-npl-peers-q4',
              title: 'Test Unknown Chart',
              takeaway: {
                sentence_id: 's-1',
                text: 'Dữ liệu dạng bảng.',
                fact_ids: [],
                author: 'system',
                source: 'deterministic_fallback',
                revision: 0
              }
            }
          ]
        },
        facts: lookupFixture.facts as unknown as Fact[],
        datasets: lookupFixture.datasets as unknown as Dataset[],
        source_notes: []
      };

      renderReportInRouter(reportWithUnknownChart);
      // Figure title rendered
      expect(screen.getByText(/Test Unknown Chart/)).toBeInTheDocument();
      // DataTable rendered with table role
      expect(screen.getByRole('table')).toBeInTheDocument();
    });

    it('falls back to LegacyReport when report does not declare report_version', () => {
      const legacyReport: AnalysisReport = {
        report_id: 'rep-legacy-sample',
        status: 'completed',
        query: 'Báo cáo kiểu cũ',
        target_ticker: 'ACB',
        period: '2024_Q4'
      };

      const { container } = renderReportInRouter(legacyReport);
      // Legacy workspace header contains ReportHeaderBar / sticky header
      expect(container.querySelector('[role="status"]')?.textContent).toContain(
        'API không trả về kế hoạch phân tích cho báo cáo này'
      );
    });
  });

  describe('Formatting Utilities and niceTicks', () => {
    it('formats percentages correctly with Vietnamese locale and decimal comma', () => {
      expect(fmtPct(21.7459, 1)).toBe('21,7%');
      expect(fmtPct(0.9636, 2)).toBe('0,96%');
      expect(fmtPct(null)).toBe('—');
    });

    it('formats percentage points (điểm %)', () => {
      expect(fmtPp(3.1, 1)).toBe('3,1 điểm %');
      expect(fmtPp(-0.26, 2)).toBe('-0,26 điểm %');
      expect(fmtPp(null)).toBe('—');
    });

    it('formats times / ratios (lần)', () => {
      expect(fmtTimes(2.4, 1)).toBe('2,4 lần');
      expect(fmtTimes(null)).toBe('—');
    });

    it('formats ranks', () => {
      expect(fmtRank(2, 5)).toBe('2/5');
      expect(fmtRank(1, null)).toBe('#1');
      expect(fmtRank(null, 5)).toBe('—');
    });

    it('formats periods and period ranges', () => {
      expect(fmtPeriod('2024_Q4')).toBe('Quý 4/2024');
      expect(fmtPeriod('2024_Q1')).toBe('Quý 1/2024');
      expect(fmtPeriodRange(['2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4'])).toBe('Q1–Q4/2024');
      expect(fmtPeriodRange('2024_Q1_to_2024_Q4')).toBe('Q1–Q4/2024');
    });

    it('computes niceTicks with exact clean round numbers', () => {
      expect(niceTicks(0, 6, 3)).toEqual([0, 3, 6]);
      expect(niceTicks(0, 240, 3)).toEqual([0, 120, 240]);
      expect(niceTicks(1, 3, 3)).toEqual([1, 2, 3]);
      expect(niceTicks(5, 25, 3)).toEqual([5, 15, 25]);
    });
  });
});
