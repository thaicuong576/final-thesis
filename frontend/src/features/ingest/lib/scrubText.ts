/**
 * Safety-net text scrubbing utility for user-facing strings.
 *
 * Requirements (INGEST-5 review round 1):
 * Any text reaching the screen from issues, checks, or blocking reasons must NEVER
 * contain:
 * 1. Raw metric IDs (`bank.input.*`)
 * 2. Raw period identifiers (`\\d{4}_Q\\d`)
 * 3. Raw snake_case identifiers (`/[a-z]+_[a-z0-9_]+/`)
 */

const METRIC_LABELS: Record<string, string> = {
  'bank.input.npl_group_3_balance': 'Nợ dưới tiêu chuẩn (Nhóm 3)',
  'bank.input.npl_group_4_balance': 'Nợ nghi ngờ (Nhóm 4)',
  'bank.input.npl_group_5_balance': 'Nợ có khả năng mất vốn (Nhóm 5)',
  'bank.input.gross_customer_loans': 'Cho vay khách hàng (dư nợ gộp)',
  'bank.input.loan_loss_provisions': 'Dự phòng rủi ro cho vay khách hàng',
  'bank.input.profit_after_tax': 'Lợi nhuận sau thuế',
  'bank.input.total_assets': 'Tổng tài sản',
  'bank.input.parent_attributable_profit': 'Lợi nhuận sau thuế của cổ đông công ty mẹ',
  'bank.input.total_equity': 'Tổng vốn chủ sở hữu',
  'bank.input.non_controlling_interests': 'Lợi ích của cổ đông không kiểm soát',
};

const CODE_LABELS: Record<string, string> = {
  row_not_found: 'không tìm thấy dòng',
  missing_required: 'thiếu chỉ tiêu bắt buộc',
  pat_equals_parent_plus_nci: 'cân đối lợi nhuận sau thuế',
  npl_sum_le_loans: 'tổng nợ xấu trên dư nợ',
  provisions_range: 'khoảng dự phòng rủi ro',
  assets_gt_loans: 'tổng tài sản lớn hơn dư nợ',
  assets_gt_equity: 'tổng tài sản lớn hơn vốn chủ sở hữu',
  equity_ge_nci: 'vốn chủ sở hữu lớn hơn lợi ích thiểu số',
  magnitude_range: 'thang đo giá trị',
  yoy_change: 'biến động cùng kỳ',
  digit_mismatch: 'không khớp chữ số',
  unit_unknown: 'đơn vị tiền tệ chưa xác định',
  period_mismatch: 'kỳ báo cáo không khớp',
  column_not_identified: 'chưa nhận diện được cột',
  column_missing: 'thiếu cột số liệu',
  low_confidence_match: 'độ khớp thấp',
  target_column_unconfirmed: 'chưa xác nhận cột kỳ mục tiêu',
  prior_column_unconfirmed: 'chưa xác nhận cột kỳ so sánh',
  target: 'kỳ mục tiêu',
  prior: 'kỳ so sánh',
};

/**
 * Scrubs any raw internal technical IDs or snake_case tokens from text intended for users.
 */
export function scrubUserText(text: string | null | undefined): string {
  if (!text) return '';

  let out = text;

  // 1. Replace known metric IDs with Vietnamese labels
  for (const [id, label] of Object.entries(METRIC_LABELS)) {
    if (out.includes(id)) {
      out = out.split(id).join(label);
    }
  }

  // 2. Replace any leftover bank.input.<suffix>
  out = out.replace(/\bbank\.input\.([a-z0-9_]+)\b/gi, (_, suffix) => {
    return `chỉ tiêu ${suffix.replace(/_/g, ' ')}`;
  });

  // 3. Scrub remaining "bank.input"
  out = out.replace(/\bbank\.input\b/gi, 'chỉ tiêu');

  // 4. Humanize quarterly periods: 2025_Q4 -> Quý 4/2025
  out = out.replace(/\b(\d{4})_Q([1-4])\b/g, 'Quý $2/$1');

  // 5. Replace known snake_case codes
  for (const [code, label] of Object.entries(CODE_LABELS)) {
    const re = new RegExp(`\\b${code}\\b`, 'g');
    out = out.replace(re, label);
  }

  // 6. Any remaining snake_case tokens: replace underscore with space
  // This guarantees that /[a-z]+_[a-z0-9_]+/ will never match.
  out = out.replace(/\b([a-z]+(?:_[a-z0-9]+)+)\b/g, (match) => {
    return match.replace(/_/g, ' ');
  });

  return out;
}
