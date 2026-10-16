import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { scrubUserText } from '@/features/ingest/lib/scrubText';
import { ExtractedRowsTable } from '@/features/ingest/components/ExtractedRowsTable';
import { ValidationPanel } from '@/features/ingest/components/ValidationPanel';
import type { Row, Validation } from '@/features/ingest/model/types';

describe('scrubUserText utility (INGEST-5 Review Round 1)', () => {
  it('scrubs raw bank.input IDs and replaces them with Vietnamese labels', () => {
    const raw = 'Không tìm thấy dòng tương ứng với chỉ tiêu bank.input.npl_group_3_balance.';
    const scrubbed = scrubUserText(raw);

    expect(scrubbed).not.toContain('bank.input');
    expect(scrubbed).not.toMatch(/[a-z]+_[a-z0-9_]+/);
    expect(scrubbed).toContain('Nợ dưới tiêu chuẩn (Nhóm 3)');
  });

  it('scrubs raw period codes like 2025_Q4 to Quý 4/2025', () => {
    const raw = 'Không tìm thấy cột số liệu cho kỳ 2025_Q4 trên dòng này.';
    const scrubbed = scrubUserText(raw);

    expect(scrubbed).not.toContain('2025_Q4');
    expect(scrubbed).toContain('Quý 4/2025');
    expect(scrubbed).not.toMatch(/[a-z]+_[a-z0-9_]+/);
  });

  it('converts any arbitrary snake_case error code to spaced readable text', () => {
    const raw = 'Cảnh báo target_column_unconfirmed và row_not_found từ hệ thống.';
    const scrubbed = scrubUserText(raw);

    expect(scrubbed).not.toMatch(/[a-z]+_[a-z0-9_]+/);
    expect(scrubbed).not.toContain('target_column_unconfirmed');
    expect(scrubbed).not.toContain('row_not_found');
  });
});

describe('UI Rendering of Missing Row Issues & Validation Checks', () => {
  it('renders missing row issue without bank.input and without snake_case', () => {
    const missingRow: Row = {
      row_id: 'bank.input.npl_group_3_balance:target',
      metric_id: 'bank.input.npl_group_3_balance',
      label_vi: 'Nợ dưới tiêu chuẩn (Nhóm 3)',
      period_role: 'target',
      period_id: '2025_Q4',
      value_billion_vnd: null,
      extracted_value_billion_vnd: null,
      raw_text: null,
      row_label: null,
      page: null,
      source: null,
      status: 'missing',
      edited: false,
      confirmed: false,
      issues: [
        {
          code: 'row_not_found',
          severity: 'error',
          message_vi: 'Không tìm thấy dòng tương ứng với chỉ tiêu bank.input.npl_group_3_balance.',
        },
      ],
      alternatives: [],
    };

    const { container } = render(
      <ExtractedRowsTable
        rows={[missingRow]}
        onUpdateRow={async () => {}}
        onSelectPage={() => {}}
        selectedPage={null}
      />
    );

    expect(container.textContent).not.toContain('bank.input');
    expect(container.textContent).not.toMatch(/[a-z]+_[a-z0-9_]+/);

    // Look for the rendered issue message (present in both desktop table and mobile card views)
    const issueElements = screen.getAllByText(/Không tìm thấy dòng tương ứng với chỉ tiêu/);
    expect(issueElements.length).toBeGreaterThan(0);

    for (const el of issueElements) {
      const renderedIssueText = el.textContent || '';
      expect(renderedIssueText).not.toContain('bank.input');
      expect(renderedIssueText).not.toMatch(/[a-z]+_[a-z0-9_]+/);
      expect(renderedIssueText).toContain('Nợ dưới tiêu chuẩn (Nhóm 3)');
    }
  });

  it('renders validation panel checks without bank.input and without snake_case', () => {
    const mockValidation: Validation = {
      status: 'fail',
      ready_to_confirm: false,
      blocking_reasons_vi: [
        'Lợi nhuận sau thuế không khớp pat_equals_parent_plus_nci kỳ target.',
      ],
      checks: [
        {
          code: 'pat_equals_parent_plus_nci',
          severity: 'error',
          message_vi: 'Lỗi pat_equals_parent_plus_nci đối với bank.input.profit_after_tax.',
          row_ids: ['bank.input.profit_after_tax:target'],
        },
      ],
    };

    const { container } = render(
      <ValidationPanel
        validation={mockValidation}
        onHighlightRows={() => {}}
      />
    );

    const text = container.textContent || '';
    expect(text).not.toContain('bank.input');
    expect(text).not.toMatch(/[a-z]+_[a-z0-9_]+/);
  });
});
