/**
 * INGEST-3 types — generated from CONTRACT.md 2026-10-16.
 * Source of truth: docs/plans/2026-10-16-filing-ingest/CONTRACT.md
 */

export type FilingStatus = 'processing' | 'ready' | 'failed';
export type RowStatus = 'candidate' | 'needs_review' | 'missing';
export type PeriodRole = 'target' | 'prior';
export type OcrProvider = 'text_layer' | 'tesseract' | 'llamaparse' | 'mixed' | 'sample';
export type IssueSeverity = 'error' | 'warning' | 'info';
export type ValidationStatus = 'pass' | 'warn' | 'fail';
export type RowSource = 'text_layer' | 'ocr' | 'llamaparse' | 'user' | null;
export type FilingErrorCode =
  | 'ocr_unavailable'
  | 'not_a_pdf'
  | 'encrypted'
  | 'no_statements_found'
  | 'provider_error';

export const METRIC_IDS = [
  'bank.input.npl_group_3_balance',
  'bank.input.npl_group_4_balance',
  'bank.input.npl_group_5_balance',
  'bank.input.gross_customer_loans',
  'bank.input.loan_loss_provisions',
  'bank.input.profit_after_tax',
  'bank.input.total_assets',
  'bank.input.parent_attributable_profit',
  'bank.input.total_equity',
  'bank.input.non_controlling_interests',
] as const;

export type MetricId = (typeof METRIC_IDS)[number];

export const METRIC_LABELS: Record<MetricId, string> = {
  'bank.input.npl_group_3_balance': 'Nợ nhóm 3',
  'bank.input.npl_group_4_balance': 'Nợ nhóm 4',
  'bank.input.npl_group_5_balance': 'Nợ nhóm 5',
  'bank.input.gross_customer_loans': 'Dư nợ cho vay gộp',
  'bank.input.loan_loss_provisions': 'Dự phòng rủi ro cho vay',
  'bank.input.profit_after_tax': 'Lợi nhuận sau thuế',
  'bank.input.total_assets': 'Tổng tài sản',
  'bank.input.parent_attributable_profit': 'Lợi nhuận thuộc công ty mẹ',
  'bank.input.total_equity': 'Tổng vốn chủ sở hữu',
  'bank.input.non_controlling_interests': 'Lợi ích cổ đông không kiểm soát',
};

export interface Issue {
  code: string;
  severity: IssueSeverity;
  message_vi: string;
}

export interface RowAlternative {
  value_billion_vnd: string;
  raw_text: string;
  row_label: string;
  page: number;
}

export interface Row {
  row_id: string;
  metric_id: MetricId;
  label_vi: string;
  period_role: PeriodRole;
  period_id: string;
  value_billion_vnd: string | null;
  extracted_value_billion_vnd: string | null;
  raw_text: string | null;
  row_label: string | null;
  page: number | null;
  source: RowSource;
  status: RowStatus;
  edited: boolean;
  confirmed: boolean;
  issues: Issue[];
  alternatives: RowAlternative[];
}

export interface ValidationCheck {
  code: string;
  severity: IssueSeverity;
  message_vi: string;
  row_ids: string[];
  expected?: string;
  actual?: string;
}

export interface Validation {
  status: ValidationStatus;
  ready_to_confirm: boolean;
  blocking_reasons_vi: string[];
  checks: ValidationCheck[];
}

export interface FilingProgress {
  pages_done: number;
  page_count: number;
}

export interface StatementPages {
  balance_sheet: number[];
  income_statement: number[];
  loan_quality_note: number[];
}

export type UnitDetected = 'billion_vnd' | 'million_vnd' | 'thousand_vnd' | 'vnd' | null;

export interface Filing {
  filing_id: string;
  status: FilingStatus;
  error_code?: FilingErrorCode;
  message_vi?: string;
  filename: string;
  sha256: string;
  page_count: number;
  entity_id: string;
  display_name: string;
  fiscal_year: number;
  reporting_scope: 'consolidated' | 'separate';
  ocr_provider: OcrProvider;
  progress: FilingProgress;
  statement_pages: StatementPages;
  unit_detected: UnitDetected;
  rows: Row[];
  validation: Validation;
  limitations_vi: string[];
}

export interface FilingSummary {
  filing_id: string;
  entity_id: string;
  display_name: string;
  fiscal_year: number;
  status: FilingStatus;
  created_at: string;
  filename: string;
}

export interface FilingSample {
  sample_id: string;
  title_vi: string;
  entity_id: string;
  fiscal_year: number;
  page_count: number;
  note_vi: string;
}

/** Subset of the existing UploadResponse from BankUploadSection */
export interface ConfirmResult {
  upload_id: string;
  entity_id: string;
  display_name: string;
  status: 'accepted' | 'rejected';
  period_id: string;
  metrics: Array<{
    metric_id: string;
    computed_value: number;
    reported_value: number | null;
    status: string;
  }>;
  row_issues: Array<{ row: number; field: string; message_vi: string }>;
  limitations_vi: string;
}

export interface PutRowBody {
  value_billion_vnd: string | null;
  confirmed: boolean;
}

export type WizardStep =
  | 'upload'
  | 'processing'
  | 'pages'
  | 'rows'
  | 'validation'
  | 'confirm'
  | 'done';
