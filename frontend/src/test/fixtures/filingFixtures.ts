/**
 * Fixtures for INGEST-3 tests.
 * Numbers from data/onboarding/top10-2025/ACB-2025q4.csv (real observed values).
 * See CONTRACT.md 2026-10-16 for schema.
 */

import type { Filing, FilingSample, Row, Validation } from '@/features/ingest/model/types';

// ------------------------------------------------------------------
// Minimal empty validation helper
// ------------------------------------------------------------------
function emptyValidation(ready = false): Validation {
  return {
    status: ready ? 'pass' : 'fail',
    ready_to_confirm: ready,
    blocking_reasons_vi: ready ? [] : ['Còn dòng chưa xác nhận'],
    checks: [],
  };
}

// ------------------------------------------------------------------
// Real ACB 2025 rows (target = 2025_Q4, prior = 2024_Q4)
// All values in billion_vnd as strings per CONTRACT.md
// ------------------------------------------------------------------
function makeRow(
  metricId: string,
  labelVi: string,
  periodRole: 'target' | 'prior',
  periodId: string,
  value: string,
  page: number,
  rowLabel: string,
  overrides: Partial<Row> = {}
): Row {
  return {
    row_id: `${metricId}:${periodRole}`,
    metric_id: metricId as Row['metric_id'],
    label_vi: labelVi,
    period_role: periodRole,
    period_id: periodId,
    value_billion_vnd: value,
    extracted_value_billion_vnd: value,
    raw_text: value,
    row_label: rowLabel,
    page,
    source: 'ocr',
    status: 'candidate',
    edited: false,
    confirmed: false,
    issues: [],
    alternatives: [],
    ...overrides,
  };
}

const ACB_ROWS_CLEAN: Row[] = [
  makeRow('bank.input.npl_group_3_balance', 'Nợ nhóm 3', 'target', '2025_Q4', '764.791', 50, 'Nhóm 3 - Nợ dưới tiêu chuẩn'),
  makeRow('bank.input.npl_group_3_balance', 'Nợ nhóm 3', 'prior', '2024_Q4', '700.000', 50, 'Nhóm 3 - Nợ dưới tiêu chuẩn'),
  makeRow('bank.input.npl_group_4_balance', 'Nợ nhóm 4', 'target', '2025_Q4', '770.229', 50, 'Nhóm 4 - Nợ nghi ngờ'),
  makeRow('bank.input.npl_group_4_balance', 'Nợ nhóm 4', 'prior', '2024_Q4', '680.000', 50, 'Nhóm 4 - Nợ nghi ngờ'),
  makeRow('bank.input.npl_group_5_balance', 'Nợ nhóm 5', 'target', '2025_Q4', '5136.367', 50, 'Nhóm 5 - Nợ có khả năng mất vốn'),
  makeRow('bank.input.npl_group_5_balance', 'Nợ nhóm 5', 'prior', '2024_Q4', '5000.000', 50, 'Nhóm 5 - Nợ có khả năng mất vốn'),
  makeRow('bank.input.gross_customer_loans', 'Dư nợ cho vay gộp', 'target', '2025_Q4', '669436.647', 50, 'Tổng nhóm 1-5'),
  makeRow('bank.input.gross_customer_loans', 'Dư nợ cho vay gộp', 'prior', '2024_Q4', '580000.000', 50, 'Tổng nhóm 1-5'),
  makeRow('bank.input.loan_loss_provisions', 'Dự phòng rủi ro cho vay', 'target', '2025_Q4', '7507.253', 51, 'Dự phòng cụ thể + dự phòng chung'),
  makeRow('bank.input.loan_loss_provisions', 'Dự phòng rủi ro cho vay', 'prior', '2024_Q4', '6800.000', 51, 'Dự phòng cụ thể + dự phòng chung'),
  makeRow('bank.input.profit_after_tax', 'Lợi nhuận sau thuế', 'target', '2025_Q4', '15624.699', 10, 'Lợi nhuận sau thuế Năm 2025'),
  makeRow('bank.input.profit_after_tax', 'Lợi nhuận sau thuế', 'prior', '2024_Q4', '16789.768', 10, 'Lợi nhuận sau thuế Năm 2024'),
  makeRow('bank.input.total_assets', 'Tổng tài sản', 'target', '2025_Q4', '1025850.127', 7, 'Tổng tài sản 31.12.2025'),
  makeRow('bank.input.total_assets', 'Tổng tài sản', 'prior', '2024_Q4', '864005.703', 7, 'Tổng tài sản 31.12.2024'),
  makeRow('bank.input.parent_attributable_profit', 'Lợi nhuận thuộc công ty mẹ', 'target', '2025_Q4', '15624.699', 10, 'Lợi nhuận thuộc cổ đông mẹ 2025'),
  makeRow('bank.input.parent_attributable_profit', 'Lợi nhuận thuộc công ty mẹ', 'prior', '2024_Q4', '16789.768', 10, 'Lợi nhuận thuộc cổ đông mẹ 2024'),
  makeRow('bank.input.total_equity', 'Tổng vốn chủ sở hữu', 'target', '2025_Q4', '94519.719', 8, 'Tổng vốn chủ sở hữu 31.12.2025'),
  makeRow('bank.input.total_equity', 'Tổng vốn chủ sở hữu', 'prior', '2024_Q4', '83461.678', 8, 'Tổng vốn chủ sở hữu 31.12.2024'),
  makeRow('bank.input.non_controlling_interests', 'Lợi ích cổ đông không kiểm soát', 'target', '2025_Q4', '0.000', 8, 'Lợi ích CĐKKS 31.12.2025'),
  makeRow('bank.input.non_controlling_interests', 'Lợi ích cổ đông không kiểm soát', 'prior', '2024_Q4', '0.000', 8, 'Lợi ích CĐKKS 31.12.2024'),
];

// ------------------------------------------------------------------
// Scenario: clean ready, all confirmed
// ------------------------------------------------------------------
export const filingClean: Filing = {
  filing_id: 'fl-acb2025clean001',
  status: 'ready',
  filename: 'ACB-BCTC-2025-Hopnhat.pdf',
  sha256: 'abc123',
  page_count: 120,
  entity_id: 'ACB',
  display_name: 'Ngân hàng Á Châu (ACB)',
  fiscal_year: 2025,
  reporting_scope: 'consolidated',
  ocr_provider: 'tesseract',
  progress: { pages_done: 120, page_count: 120 },
  statement_pages: {
    balance_sheet: [7, 8],
    income_statement: [10, 11],
    loan_quality_note: [50, 51],
  },
  unit_detected: 'billion_vnd',
  rows: ACB_ROWS_CLEAN.map((r) => ({ ...r, confirmed: true, status: 'candidate' })),
  validation: {
    status: 'pass',
    ready_to_confirm: true,
    blocking_reasons_vi: [],
    checks: [],
  },
  limitations_vi: ['Ngân hàng tải lên không được tính vào trung vị nhóm.'],
};

// ------------------------------------------------------------------
// Scenario: needs_review row + missing row + validation error
// ------------------------------------------------------------------
const rowsWithIssue: Row[] = ACB_ROWS_CLEAN.map((r, i) => {
  // Dự phòng target: needs_review, has alternatives
  if (r.row_id === 'bank.input.loan_loss_provisions:target') {
    return {
      ...r,
      status: 'needs_review',
      confirmed: false,
      value_billion_vnd: '7507.253',
      issues: [{ code: 'value_in_page_text', severity: 'warning', message_vi: 'Có 2 ứng viên trùng trang, hãy xác nhận.' }],
      alternatives: [
        { value_billion_vnd: '2525.003', raw_text: '2.525.003', row_label: 'Dự phòng cụ thể', page: 51 },
        { value_billion_vnd: '4982.250', raw_text: '4.982.250', row_label: 'Dự phòng chung', page: 51 },
      ],
    } satisfies Row;
  }
  // NCI prior: missing
  if (r.row_id === 'bank.input.non_controlling_interests:prior' && i > 0) {
    return {
      ...r,
      status: 'missing',
      confirmed: false,
      value_billion_vnd: null,
      extracted_value_billion_vnd: null,
      raw_text: null,
      issues: [{ code: 'missing_required', severity: 'error', message_vi: 'Không tìm thấy giá trị; cần nhập thủ công.' }],
    } satisfies Row;
  }
  // Others: confirmed (to isolate the issues)
  return { ...r, confirmed: true };
});

export const filingWithIssues: Filing = {
  ...filingClean,
  filing_id: 'fl-acb2025issues002',
  rows: rowsWithIssue,
  validation: {
    status: 'fail',
    ready_to_confirm: false,
    blocking_reasons_vi: [
      'Còn 1 dòng thiếu cần nhập thủ công.',
      'Còn 1 dòng cần xem lại cần xác nhận.',
    ],
    checks: [
      {
        code: 'missing_required',
        severity: 'error',
        message_vi: 'Dòng "Lợi ích cổ đông không kiểm soát (kỳ trước)" bị thiếu.',
        row_ids: ['bank.input.non_controlling_interests:prior'],
      },
      {
        code: 'pat_equals_parent_plus_nci',
        severity: 'warning',
        message_vi: 'Lợi nhuận sau thuế ≠ Lợi nhuận công ty mẹ + Lợi ích CĐKKS (kỳ trước). Chênh lệch 0 đồng khi NCI = 0.',
        row_ids: [
          'bank.input.profit_after_tax:prior',
          'bank.input.parent_attributable_profit:prior',
          'bank.input.non_controlling_interests:prior',
        ],
      },
    ],
  },
};

// ------------------------------------------------------------------
// Scenario: processing in-progress
// ------------------------------------------------------------------
export const filingProcessing: Filing = {
  ...filingClean,
  filing_id: 'fl-acb2025proc003',
  status: 'processing',
  rows: [],
  validation: emptyValidation(false),
  progress: { pages_done: 37, page_count: 120 },
  limitations_vi: [],
  statement_pages: { balance_sheet: [], income_statement: [], loan_quality_note: [] },
};

// ------------------------------------------------------------------
// Scenario: failed — OCR unavailable
// ------------------------------------------------------------------
export const filingFailed: Filing = {
  ...filingClean,
  filing_id: 'fl-acb2025fail004',
  status: 'failed',
  error_code: 'ocr_unavailable',
  message_vi: 'Máy chủ chưa cài công cụ OCR (Tesseract). Liên hệ quản trị viên hoặc dùng bộ mẫu để trình diễn.',
  rows: [],
  validation: emptyValidation(false),
  progress: { pages_done: 0, page_count: 0 },
  limitations_vi: [],
  statement_pages: { balance_sheet: [], income_statement: [], loan_quality_note: [] },
};

// ------------------------------------------------------------------
// Scenarios for Playwright / component tests
// ------------------------------------------------------------------
export const FILING_SCENARIOS: Record<string, Filing> = {
  clean: filingClean,
  issues: filingWithIssues,
  processing: filingProcessing,
  failed: filingFailed,
};

// ------------------------------------------------------------------
// Sample entries (used by GET /api/onboarding/filing-samples)
// ------------------------------------------------------------------
export const FILING_SAMPLES: FilingSample[] = [
  {
    sample_id: 'acb-2025-clean',
    title_vi: 'ACB 2025 — đọc sạch (mẫu)',
    entity_id: 'ACB',
    fiscal_year: 2025,
    page_count: 120,
    note_vi: 'Tất cả 20 dòng đều đọc thành công, 0 dòng cần xem lại.',
  },
  {
    sample_id: 'acb-2025-issues',
    title_vi: 'ACB 2025 — có dòng cần xem lại (mẫu)',
    entity_id: 'ACB',
    fiscal_year: 2025,
    page_count: 120,
    note_vi: '1 dòng cần xem lại, 1 dòng thiếu, 1 lỗi kiểm tra.',
  },
  {
    sample_id: 'acb-2025-processing',
    title_vi: 'ACB 2025 — đang đọc báo cáo (mẫu)',
    entity_id: 'ACB',
    fiscal_year: 2025,
    page_count: 120,
    note_vi: 'Trình diễn thanh tiến độ và thông tin công cụ OCR.',
  },
];
