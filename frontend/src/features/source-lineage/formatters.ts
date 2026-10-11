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
  const unitSuffix = receipt.unit === "percent" || unit === "%" ? "%" : "";

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

  // 3. Generic formula based on ordered inputs
  const formattedInputs = inputs.map((inp) => formatNumber(parseFloat(inp.value), 1));
  return `${formattedInputs.join(" / ")} = ${outputVal}${unitSuffix}`;
}
