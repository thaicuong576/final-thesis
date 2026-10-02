import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EquityReportProvider } from '../src/features/equity-report/components/EquityReportContext';
import { Headline } from '../src/features/equity-report/components/Headline';
import { SentenceView } from '../src/features/equity-report/components/SentenceView';
import { SourceNotes } from '../src/features/equity-report/components/SourceNotes';
import type { AdaptiveReportResponse, SourceNote, Fact } from '../src/features/equity-report';

describe('Report Citation Superscripts and Caps (CITE-1)', () => {
  const tenNotes: SourceNote[] = Array.from({ length: 10 }, (_, i) => ({
    note_no: i + 1,
    source_id: `src-${i + 1}`,
    title: `Nguồn BCTC số ${i + 1}`,
    url: null,
    locator: `tr. ${i + 1}`,
    fact_ids: [`fact-${i + 1}`]
  }));

  const tenFacts: Fact[] = Array.from({ length: 10 }, (_, i) => ({
    fact_id: `fact-${i + 1}`,
    fact_type: 'value',
    entity_id: 'ACB',
    other_entity_id: null,
    universe_id: null,
    metric_id: `metric.${i + 1}`,
    period: '2024_Q4',
    from_period: null,
    value: 10 + i,
    unit: '%',
    rank_better: null,
    rank_desc: null,
    denominator: null,
    formula_version: 'v1',
    input_observation_ids: [],
    input_fact_ids: []
  }));

  const mockReport: AdaptiveReportResponse = {
    report_id: 'test-cite-cap',
    status: 'completed',
    report_version: 'er-report-v1',
    question_type: 'company_profile',
    facts: tenFacts,
    source_notes: tenNotes,
    datasets: []
  } as unknown as AdaptiveReportResponse;

  it('headline renders zero citation numbers', () => {
    const { container } = render(
      <EquityReportProvider report={mockReport}>
        <Headline
          block={{
            type: 'headline',
            sentence: {
              sentence_id: 'hl-1',
              text: 'ACB: đệm dự phòng trên nhóm, chất lượng nợ trên nhóm trong quý 2/2026.',
              fact_ids: tenNotes.map((n) => `fact-${n.note_no}`),
              author: 'orchestrator',
              source: 'model',
              revision: 0
            }
          }}
        />
      </EquityReportProvider>
    );

    const h1 = container.querySelector('h1');
    expect(h1).not.toBeNull();
    expect(h1?.textContent).toBe('ACB: đệm dự phòng trên nhóm, chất lượng nợ trên nhóm trong quý 2/2026.');
    expect(container.querySelectorAll('h1 sup').length).toBe(0);
    expect(container.querySelectorAll('h1 a').length).toBe(0);
  });

  it('a sentence with 2 sources renders 1,2 and no +N', () => {
    const { container } = render(
      <EquityReportProvider report={mockReport}>
        <SentenceView
          sentence={{
            sentence_id: 'sent-2',
            text: 'Tỷ lệ bao phủ nợ xấu của ACB đạt 105,3% trong quý 2/2026.',
            fact_ids: ['fact-1', 'fact-2'],
            author: 'company',
            source: 'model',
            revision: 0
          }}
        />
      </EquityReportProvider>
    );

    const sup = container.querySelector('sup');
    expect(sup).not.toBeNull();
    expect(sup?.textContent).toBe('1,2');

    const links = sup?.querySelectorAll('a');
    expect(links?.length).toBe(2);
    expect(links?.[0].getAttribute('href')).toBe('#note-1');
    expect(links?.[0].textContent).toBe('1');
    expect(links?.[1].getAttribute('href')).toBe('#note-2');
    expect(links?.[1].textContent).toBe('2');

    // No +N marker rendered
    expect(sup?.textContent).not.toContain('+');
    expect(container.querySelector('a[href="#source-notes"]')).toBeNull();
  });

  it('a sentence with 10 sources renders 3 numbers and +7 with the aria-label listing the 7 hidden numbers', () => {
    const { container } = render(
      <EquityReportProvider report={mockReport}>
        <SentenceView
          sentence={{
            sentence_id: 'sent-10',
            text: 'ACB xếp hạng 4/10 về tỷ lệ bao phủ nợ xấu trong quý 2/2026.',
            fact_ids: tenNotes.map((n) => `fact-${n.note_no}`),
            author: 'company',
            source: 'model',
            revision: 0
          }}
        />
      </EquityReportProvider>
    );

    const sup = container.querySelector('sup');
    expect(sup).not.toBeNull();
    expect(sup?.textContent).toBe('1,2,3 +7');

    const visibleLinks = sup?.querySelectorAll('a[href^="#note-"]');
    expect(visibleLinks?.length).toBe(3);
    expect(visibleLinks?.[0].textContent).toBe('1');
    expect(visibleLinks?.[1].textContent).toBe('2');
    expect(visibleLinks?.[2].textContent).toBe('3');

    const plusMarker = sup?.querySelector('a[href="#source-notes"]');
    expect(plusMarker).not.toBeNull();
    expect(plusMarker?.textContent).toBe('+7');
    expect(plusMarker?.getAttribute('aria-label')).toBe('Và 7 nguồn khác: 4, 5, 6, 7, 8, 9, 10');
    expect(plusMarker?.getAttribute('title')).toBe('Và 7 nguồn khác: 4, 5, 6, 7, 8, 9, 10');
  });

  it('+N marker is keyboard focusable and jumps to the Nguồn section', () => {
    const { container } = render(
      <EquityReportProvider report={mockReport}>
        <SentenceView
          sentence={{
            sentence_id: 'sent-10',
            text: 'ACB xếp hạng 4/10.',
            fact_ids: tenNotes.map((n) => `fact-${n.note_no}`),
            author: 'company',
            source: 'model',
            revision: 0
          }}
        />
        <SourceNotes />
      </EquityReportProvider>
    );

    const plusMarker = container.querySelector('a[href="#source-notes"]') as HTMLAnchorElement;
    expect(plusMarker).not.toBeNull();

    // In DOM, an anchor with href is keyboard focusable
    plusMarker.focus();
    expect(document.activeElement).toBe(plusMarker);

    // Target section #source-notes exists in the document
    const sourceSection = container.querySelector('#source-notes');
    expect(sourceSection).not.toBeNull();
    expect(sourceSection?.getAttribute('aria-label')).toBe('Nguồn số liệu');
  });
});
