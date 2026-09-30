import fs from 'fs';
import path from 'path';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { ReportPage } from '../src/pages/reports/ReportPage';
import { AdaptiveReport, type AdaptiveReportResponse } from '../src/features/equity-report';

// Real staging fixtures from commit db6762f (ER-4 model responses)
import realB1 from '../src/test/fixtures/real-staging-b1.json';
import realB2 from '../src/test/fixtures/real-staging-b2.json';
import realB3 from '../src/test/fixtures/real-staging-b3.json';
import realB4 from '../src/test/fixtures/real-staging-b4.json';
import realB5 from '../src/test/fixtures/real-staging-b5.json';

const REAL_FIXTURES = [
  { name: 'B1 (company_profile, ACB)', fixture: realB1 as unknown as AdaptiveReportResponse },
  { name: 'B2 (ranking, LLR Coverage)', fixture: realB2 as unknown as AdaptiveReportResponse },
  { name: 'B3 (trend, VPB ROE)', fixture: realB3 as unknown as AdaptiveReportResponse },
  { name: 'B4 (head_to_head, ACB vs TCB)', fixture: realB4 as unknown as AdaptiveReportResponse },
  { name: 'B5 (lookup, VCB NPL)', fixture: realB5 as unknown as AdaptiveReportResponse },
];

function renderReportInRouter(report: AdaptiveReportResponse) {
  return render(
    <MemoryRouter initialEntries={[`/reports/${report.report_id || 'test-report'}`]}>
      <Routes>
        <Route path="/reports/:id" element={<ReportPage report={report} />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ER-7b: Real Staging Responses (B1–B5)', () => {
  it.each(REAL_FIXTURES)('renders $name without errors', ({ fixture }) => {
    const { container } = renderReportInRouter(fixture);
    expect(container).toBeInTheDocument();
  });

  it.each(REAL_FIXTURES)(
    'sanitizes raw machine codes from displayed text in $name',
    ({ fixture }) => {
      const { container } = renderReportInRouter(fixture);
      const text = container.textContent || '';

      // Must NOT expose raw identifiers
      expect(text).not.toContain('bank.');
      expect(text).not.toContain('2024_Q');
      expect(text).not.toContain('LLR_COVERAGE');
      expect(text).not.toContain('NPL_G35');
    }
  );

  it.each(REAL_FIXTURES)(
    'sanitizes machine codes even when TechnicalDetails is expanded in $name',
    ({ fixture }) => {
      const { container } = renderReportInRouter(fixture);
      const toggleBtn = screen.queryByRole('button', { name: /Chi tiết kỹ thuật/i });
      if (toggleBtn) {
        fireEvent.click(toggleBtn);
        const text = container.textContent || '';
        expect(text).not.toContain('bank.');
        expect(text).not.toContain('2024_Q');
        expect(text).not.toContain('LLR_COVERAGE');
        expect(text).not.toContain('NPL_G35');
      }
    }
  );

  it.each(REAL_FIXTURES)(
    'displays Vietnamese decimal format with comma in numbers for $name',
    ({ fixture }) => {
      const { container } = renderReportInRouter(fixture);
      const text = container.textContent || '';

      // There should be numbers formatted with comma decimals (e.g. 21,7% or 76,6% or 223,3% or 0,96%)
      expect(text).toMatch(/\d+,\d+/);
    }
  );

  it.each(REAL_FIXTURES)(
    'renders accepted_with_limitations gently without red alert banners in $name',
    ({ fixture }) => {
      const { container } = renderReportInRouter(fixture);

      // Verify gentle indicator is displayed
      const badge = screen.getAllByText(/Chấp nhận có giới hạn/i);
      expect(badge.length).toBeGreaterThan(0);

      // No red/danger error banners (like bg-[#c84b3f] or bg-red-600)
      const errorBanners = container.querySelectorAll('.bg-danger, .bg-red-500, .bg-red-600, .text-danger');
      expect(errorBanners.length).toBe(0);
    }
  );

  it.each(REAL_FIXTURES)(
    'does not render any source note when source_notes is empty in $name',
    ({ fixture }) => {
      const { container } = renderReportInRouter(fixture);
      // Real staging responses have source_notes: []
      // When source_notes is empty, no note items are rendered
      const noteElements = container.querySelectorAll('[id^="note-"]');
      expect(noteElements.length).toBe(0);
    }
  );

  it('renders B1 (company_profile) with Scatter axes determined by dataset.metric_ids and no medians without reference_lines', () => {
    const { container } = renderReportInRouter(realB1 as unknown as AdaptiveReportResponse);
    // Caption for Figure 2 should be sanitized
    expect(screen.getByText(/Tương quan (Bao phủ|Bao phủ nợ xấu) và (Nợ xấu|Tỷ lệ nợ xấu) · Q4\/2024/i)).toBeInTheDocument();

    // In realB1, dataset 2 metric_ids is ['bank.llr_coverage', 'bank.npl_g35']
    // Metric 0 is X axis, Metric 1 is Y axis
    expect(container.textContent).toContain('Nợ xấu (%) ↑ cao hơn');
    expect(container.textContent).toContain('Bao phủ (%) → cao hơn');

    // Without reference_lines, no median line or text
    expect(container.textContent).not.toContain('đường đứt: trung vị');
    const dashedLines = container.querySelectorAll('line[stroke-dasharray="3 3"]');
    expect(dashedLines.length).toBe(0);
  });

  it('renders Scatter with median lines when reference_lines is present', () => {
    const b1Clone = JSON.parse(JSON.stringify(realB1));
    b1Clone.datasets[1].reference_lines = [
      { kind: 'median', metric_id: 'bank.llr_coverage', value: 100 },
      { kind: 'median', metric_id: 'bank.npl_g35', value: 1.5 }
    ];
    const { container } = renderReportInRouter(b1Clone as unknown as AdaptiveReportResponse);
    expect(container.textContent).toContain('đường đứt: trung vị');
    const dashedLines = container.querySelectorAll('line[stroke-dasharray="3 3"]');
    expect(dashedLines.length).toBe(2);
  });

  it('contains no literal bank.npl_g35 or bank.llr_coverage in frontend/src/features/equity-report', () => {
    const equityReportDir = path.resolve(__dirname, '../src/features/equity-report');
    function getFiles(dir: string): string[] {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      const files: string[] = [];
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          files.push(...getFiles(fullPath));
        } else if (/\.(ts|tsx)$/.test(entry.name)) {
          files.push(fullPath);
        }
      }
      return files;
    }

    const files = getFiles(equityReportDir);
    expect(files.length).toBeGreaterThan(0);
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      expect(content).not.toContain('bank.npl_g35');
      expect(content).not.toContain('bank.llr_coverage');
    }
  });

  it('renders B5 (lookup) as AnswerCardLayout with anchor period formatted', () => {
    const { container } = renderReportInRouter(realB5 as unknown as AdaptiveReportResponse);
    expect(container.querySelector('h1')).toBeNull();
    // Answer number formatted as 0,96%
    expect(screen.getByText('0,96%')).toBeInTheDocument();
    // Masthead period should be Quý 4/2024
    const periodMatches = screen.getAllByText(/Quý 4\/2024/);
    expect(periodMatches.length).toBeGreaterThan(0);
  });

  it('ensures table and chart containers provide horizontal scroll containment on small screens', () => {
    const { container } = render(
      <div style={{ width: '375px' }}>
        <AdaptiveReport report={realB1 as unknown as AdaptiveReportResponse} />
      </div>
    );

    // Root wrapper must have overflow containment
    const rootDiv = container.querySelector('.overflow-x-hidden');
    expect(rootDiv).not.toBeNull();

    // Tables must be wrapped in overflow-x-auto
    const scrollContainers = container.querySelectorAll('.overflow-x-auto');
    expect(scrollContainers.length).toBeGreaterThan(0);
  });
});
