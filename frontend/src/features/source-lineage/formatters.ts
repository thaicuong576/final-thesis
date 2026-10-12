import type { LineageCalculationReceipt } from "./types";

/**
 * Format raw period identifiers (e.g. "2026_Q2", "2024_Q4") into standard Vietnamese labels ("Quý 2/2026", "Quý 4/2024").
 */
export function formatPeriod(period?: string | null): string {
  if (!period) return "";
  const match = period.match(/^(\d{4})_Q([1-4])$/i);
  if (match) {
    return `Quý ${match[2]}/${match[1]}`;
  }
  return period;
}

/**
 * Format numbers using Vietnamese locale conventions (dot for thousands, comma for decimals).
 */
export function formatNumber(
  num?: number | string | null,
  decimals: number = 1
): string {
  if (num == null) return "—";
  const parsed = typeof num === "number" ? num : parseFloat(String(num));
  if (isNaN(parsed)) return String(num);
  return parsed.toLocaleString("vi-VN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format raw unit identifiers (e.g. "billion_vnd", "percent") into standard Vietnamese labels ("tỷ đồng", "%").
 */
export function formatUnit(unit?: string | null): string {
  if (!unit) return "";
  const lower = unit.trim().toLowerCase();
  if (lower === "billion_vnd" || lower === "billion vnd" || lower === "ty_dong" || lower === "tỷ đồng") {
    return "tỷ đồng";
  }
  if (lower === "percent" || lower === "pct" || lower === "%") {
    return "%";
  }
  if (lower === "percentage_points" || lower === "pp" || lower === "điểm %") {
    return "điểm %";
  }
  if (lower === "rank" || lower === "hạng") {
    return "hạng";
  }
  return unit;
}

/**
 * Friendly display labels for input metric IDs in formulas.
 */
const INPUT_METRIC_SHORT_NAMES: Record<string, string> = {
  "bank.input.loan_loss_provisions": "Dự phòng",
  "bank.input.npl_g35_balance": "Nợ xấu",
  "bank.input.npl_group_3_balance": "Nhóm 3",
  "bank.input.npl_group_4_balance": "Nhóm 4",
  "bank.input.npl_group_5_balance": "Nhóm 5",
  "bank.input.gross_customer_loans": "Tổng dư nợ",
  "bank.input.total_assets": "Tổng tài sản",
  "bank.input.total_equity": "Vốn CSH",
  "bank.input.parent_attributable_equity": "Vốn CSH mẹ",
  "bank.input.profit_after_tax": "Lợi nhuận",
  "bank.input.parent_attributable_profit": "Lợi nhuận mẹ",
};

/**
 * Build substituted formula string STRICTLY from calculation receipt ordered inputs and calculated output.
 * Never uses hard-coded fallback numbers.
 */
export function buildSubstitutedFormula(
  receipt?: LineageCalculationReceipt | null,
  rootValue?: number | null,
  unit?: string | null
): string | null {
  if (!receipt || !receipt.ordered_inputs || receipt.ordered_inputs.length === 0) {
    return null;
  }

  const inputs = receipt.ordered_inputs;
  const version = receipt.formula_version || "";
  const outputVal = receipt.calculated_output
    ? formatNumber(parseFloat(receipt.calculated_output), 1)
    : rootValue != null
    ? formatNumber(rootValue, 1)
    : "";
  const rawUnit = receipt.unit || unit || "";
  const formattedUnit = formatUnit(rawUnit);
  const unitSuffix = formattedUnit === "%" ? "%" : formattedUnit ? ` ${formattedUnit}` : "";

  // 1. Division / Ratio formulas (e.g. llr-coverage, roe, roa, cir, nim, ldr, npl) with 2 inputs
  if (inputs.length === 2 && (version.includes("coverage") || version.includes("roe") || version.includes("roa") || version.includes("ratio"))) {
    const name0 = INPUT_METRIC_SHORT_NAMES[inputs[0].metric_id] || "";
    const name1 = INPUT_METRIC_SHORT_NAMES[inputs[1].metric_id] || "";
    const val0 = formatNumber(parseFloat(inputs[0].value), 1);
    const val1 = formatNumber(parseFloat(inputs[1].value), 1);

    const part0 = name0 ? `${name0} ${val0}` : val0;
    const part1 = name1 ? `${name1} ${val1}` : val1;

    let prefix = "";
    if (version.includes("llr-coverage")) prefix = "Bao phủ = ";
    else if (version.includes("roe")) prefix = "ROE = ";
    else if (version.includes("roa")) prefix = "ROA = ";

    return `${prefix}${part0} / ${part1} = ${outputVal}${unitSuffix}`;
  }

  // 2. Sum / Balance formulas (e.g. npl-g35-balance, equity sum) with 2+ inputs
  if (version.includes("balance") || version.includes("sum")) {
    const parts = inputs.map((inp) => {
      const name = INPUT_METRIC_SHORT_NAMES[inp.metric_id] || "";
      const val = formatNumber(parseFloat(inp.value), 1);
      return name ? `${name} ${val}` : val;
    });
    return `${parts.join(" + ")} = ${outputVal}${unitSuffix}`;
  }

  // 3. Aggregate formulas (spread, peer_median, peer_rank, gap_to_median, delta)
  if (version.includes("spread")) {
    if (inputs.length >= 2) {
      const maxInp = inputs[0];
      const minInp = inputs[inputs.length - 1];
      const maxVal = formatNumber(parseFloat(maxInp.value), 1);
      const minVal = formatNumber(parseFloat(minInp.value), 1);
      const maxEntity = maxInp.entity_id || "";
      const minEntity = minInp.entity_id || "";
      return `Chênh lệch = Cao nhất ${maxVal}% (${maxEntity}) - Thấp nhất ${minVal}% (${minEntity}) = ${outputVal}${unitSuffix}`;
    }
    return `Chênh lệch toàn nhóm = ${outputVal}${unitSuffix}`;
  }

  if (version.includes("peer-median")) {
    return `Trung vị ngành (${inputs.length} ngân hàng) = ${outputVal}${unitSuffix}`;
  }

  if (version.includes("peer-rank")) {
    const focalInp = inputs[0];
    const focalVal = formatNumber(parseFloat(focalInp.value), 1);
    const focalEntity = focalInp.entity_id || "";
    return `Xếp hạng: ${focalEntity} đạt ${focalVal}% (hạng ${outputVal}/${inputs.length})`;
  }

  if (version.includes("gap-to-median")) {
    const focalInp = inputs[0];
    const focalVal = formatNumber(parseFloat(focalInp.value), 1);
    const focalEntity = focalInp.entity_id || "";
    return `Chênh lệch trung vị = ${focalEntity} ${focalVal}% - TV = ${outputVal}${unitSuffix}`;
  }

  if (version.includes("delta")) {
    if (inputs.length >= 2) {
      const v2 = formatNumber(parseFloat(inputs[0].value), 1);
      const v1 = formatNumber(parseFloat(inputs[1].value), 1);
      return `Biến động kỳ = ${v2} - ${v1} = ${outputVal}${unitSuffix}`;
    }
    return `Biến động kỳ = ${outputVal}${unitSuffix}`;
  }

  // 4. Generic formula based on ordered inputs
  const formattedInputs = inputs.map((inp) => formatNumber(parseFloat(inp.value), 1));
  return `${formattedInputs.join(" / ")} = ${outputVal}${unitSuffix}`;
}

/**
 * Standard Vietnamese display names for metrics.
 */
export const METRIC_DISPLAY_NAMES_VI: Record<string, string> = {
  "bank.llr_coverage": "Tỷ lệ bao phủ nợ xấu (LLR)",
  "bank.npl_g35": "Tỷ lệ nợ xấu (nhóm 3–5)",
  "bank.roa": "Tỷ suất sinh lời trên tổng tài sản (ROA)",
  "bank.roe": "Tỷ suất sinh lời trên vốn chủ sở hữu (ROE)",
  "bank.nim": "Tỷ lệ thu nhập lãi thuần (NIM)",
  "bank.cir": "Tỷ lệ chi phí trên thu nhập (CIR)",
  "bank.ldr": "Tỷ lệ cho vay trên huy động (LDR)",
  "bank.input.loan_loss_provisions": "Dự phòng rủi ro cho vay khách hàng",
  "bank.input.npl_g35_balance": "Tổng nợ xấu (nhóm 3–5)",
  "bank.input.npl_group_3_balance": "Nợ dưới tiêu chuẩn (nhóm 3)",
  "bank.input.npl_group_4_balance": "Nợ nghi ngờ (nhóm 4)",
  "bank.input.npl_group_5_balance": "Nợ có khả năng mất vốn (nhóm 5)",
  "bank.input.gross_customer_loans": "Cho vay khách hàng",
  "bank.input.total_assets": "Tổng tài sản",
  "bank.input.total_equity": "Vốn chủ sở hữu",
  "bank.input.parent_attributable_equity": "Vốn chủ sở hữu của ngân hàng mẹ",
  "bank.input.profit_after_tax": "Lợi nhuận sau thuế",
  "bank.input.parent_attributable_profit": "Lợi nhuận sau thuế của ngân hàng mẹ",
};

/**
 * Safely resolve metric display name, never leaking raw identifiers like "bank.roe".
 */
export function getMetricDisplayName(metricId?: string | null): string {
  if (!metricId) return "Chỉ số tài chính";
  if (METRIC_DISPLAY_NAMES_VI[metricId]) {
    return METRIC_DISPLAY_NAMES_VI[metricId];
  }
  const stripped = metricId.replace(/^bank\.(input\.)?/, "").replace(/_/g, " ");
  return stripped.charAt(0).toUpperCase() + stripped.slice(1);
}

