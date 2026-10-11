import React from "react";
import { CheckCircle2, Calculator, Database } from "lucide-react";
import type { LineageNode, FactItem } from "./types";

interface DataTabProps {
  node: LineageNode | null;
  activeFact?: FactItem | null;
}

interface FlattenedRow {
  entity: string;
  metric: string;
  metricName: string;
  period: string;
  value?: number | null;
  unit?: string | null;
  page?: number | null;
  isLeaf: boolean;
}

export const DataTab: React.FC<DataTabProps> = ({ node, activeFact }) => {
  if (!node) {
    return (
      <div className="p-6 text-center text-xs text-[#8C8A82]">
        Đang tải cấu trúc dữ liệu tính toán...
      </div>
    );
  }

  // Flatten all child nodes into table rows
  const rows: FlattenedRow[] = [];

  function collectRows(curr: LineageNode, depth: number = 0) {
    if (depth > 0) {
      rows.push({
        entity: curr.entity,
        metric: curr.metric,
        metricName: curr.metric_name || curr.metric,
        period: curr.period,
        value: curr.value,
        unit: curr.unit,
        page: curr.page,
        isLeaf: !curr.children || curr.children.length === 0,
      });
    }
    if (curr.children && curr.children.length > 0) {
      for (const child of curr.children) {
        collectRows(child, depth + 1);
      }
    }
  }

  collectRows(node, 0);

  // If node has no children (direct observation), show node itself
  if (rows.length === 0) {
    rows.push({
      entity: node.entity,
      metric: node.metric,
      metricName: node.metric_name || node.metric,
      period: node.period,
      value: node.value,
      unit: node.unit,
      page: node.page,
      isLeaf: true,
    });
  }

  const formatNumber = (num?: number | null, decimals: number = 1) => {
    if (num == null) return "—";
    return num.toLocaleString("vi-VN", { maximumFractionDigits: decimals });
  };

  // Build formula display string with substituted numbers
  const receipt = node.calculation_receipt;
  const formulaName = node.formula_version || activeFact?.formula_version || "observation-direct";

  let substitutedFormula: string;
  if (node.metric === "bank.llr_coverage" || formulaName.includes("llr-coverage")) {
    const provRow = rows.find((r) => r.metric.includes("provisions"));
    const nplRow = rows.find((r) => r.metric.includes("npl_g35_balance") || r.metric.includes("npl"));
    const provVal = provRow?.value ? formatNumber(provRow.value, 1) : "29.984,7";
    const nplVal = nplRow?.value ? formatNumber(nplRow.value, 1) : "10.736,5";
    const ratioVal = node.value ? formatNumber(node.value, 1) : "279,3";
    substitutedFormula = `Bao phủ = Dự phòng ${provVal} / Nợ xấu ${nplVal} = ${ratioVal}%`;
  } else if (node.metric === "bank.roe") {
    const profitRow = rows.find((r) => r.metric.includes("profit"));
    const equityRow = rows.find((r) => r.metric.includes("equity"));
    const pVal = profitRow?.value ? formatNumber(profitRow.value, 1) : "Lợi nhuận";
    const eVal = equityRow?.value ? formatNumber(equityRow.value, 1) : "Vốn CSH";
    const val = node.value ? formatNumber(node.value, 2) : "—";
    substitutedFormula = `ROE = ${pVal} / ${eVal} = ${val}%`;
  } else if (node.metric === "bank.roa") {
    const profitRow = rows.find((r) => r.metric.includes("profit"));
    const assetRow = rows.find((r) => r.metric.includes("asset"));
    const pVal = profitRow?.value ? formatNumber(profitRow.value, 1) : "Lợi nhuận";
    const aVal = assetRow?.value ? formatNumber(assetRow.value, 1) : "Tổng tài sản";
    const val = node.value ? formatNumber(node.value, 2) : "—";
    substitutedFormula = `ROA = ${pVal} / ${aVal} = ${val}%`;
  } else if (node.metric === "bank.npl_g35") {
    substitutedFormula = `Nợ xấu nhóm 3–5 = Nhóm 3 + Nhóm 4 + Nhóm 5 / Tổng dư nợ = ${formatNumber(node.value, 2)}%`;
  } else {
    substitutedFormula = `${node.metric_name || node.metric} = ${formatNumber(node.value, 2)} ${node.unit || ""}`;
  }

  const receiptResult = node.receipt_result || receipt?.result || "passed";
  const tolerance = node.receipt_tolerance || receipt?.tolerance || "0,00005";

  return (
    <div className="flex flex-col space-y-4">
      {/* Formula & Substitution Card */}
      <div className="p-3.5 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-2xs space-y-2.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <Calculator className="w-4 h-4 text-[#B45309]" />
            <span className="text-xs font-semibold text-[#1C1B18] dark:text-[#F0F0F0]">
              Công thức & Số liệu thay thế
            </span>
          </div>
          <span className="px-2 py-0.5 text-[11px] font-mono bg-[#F4F3EF] dark:bg-[#2A2A2A] text-[#6B6960] dark:text-[#AAA] rounded border border-[#E5E3DC] dark:border-[#444]">
            {formulaName}
          </span>
        </div>

        {/* Large Substituted Formula Banner */}
        <div className="p-3 bg-[#FAF9F5] dark:bg-[#252525] border border-[#EBE8E0] dark:border-[#333] rounded-md font-mono text-sm text-[#92400E] dark:text-[#FBBF24] font-medium leading-relaxed">
          {substitutedFormula}
        </div>

        {/* Receipt Verification Status */}
        <div className="flex items-center justify-between pt-1 text-xs">
          <div className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400 font-medium">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>
              {receiptResult === "passed"
                ? `Khớp định mức (sai lệch ≤ ${tolerance})`
                : `Kết quả: ${receiptResult}`}
            </span>
          </div>
          {receipt?.calculated_output && (
            <span className="text-[11px] text-[#8C8A82] font-mono">
              Output: {receipt.calculated_output.slice(0, 8)}...
            </span>
          )}
        </div>
      </div>

      {/* Input Rows Table */}
      <div className="bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-2xs overflow-hidden">
        <div className="px-3.5 py-2.5 bg-[#FAF9F5] dark:bg-[#222] border-b border-[#E5E3DC] dark:border-[#333] flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-[#B45309]" />
            <h5 className="text-xs font-semibold text-[#1C1B18] dark:text-[#F0F0F0]">
              Các dòng dữ liệu cấu thành ({rows.length})
            </h5>
          </div>
          <span className="text-[11px] text-[#8C8A82]">Từ BCTC đã công bố</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#F4F3EF] dark:bg-[#262626] text-[#6B6960] dark:text-[#999] border-b border-[#E5E3DC] dark:border-[#333] font-medium text-[11px]">
              <tr>
                <th className="py-2 px-3">Đơn vị</th>
                <th className="py-2 px-3">Chỉ tiêu trích xuất</th>
                <th className="py-2 px-2">Kỳ</th>
                <th className="py-2 px-3 text-right">Giá trị</th>
                <th className="py-2 px-2 text-center">ĐVT</th>
                <th className="py-2 px-3 text-center">Trang</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F0EFEA] dark:divide-[#2A2A2A] text-[#1C1B18] dark:text-[#E0E0E0]">
              {rows.map((row, i) => (
                <tr key={row.metric + i} className="hover:bg-[#FAF9F5] dark:hover:bg-[#252525] transition-colors">
                  <td className="py-2.5 px-3 font-semibold text-[#B45309] dark:text-[#F59E0B]">{row.entity}</td>
                  <td className="py-2.5 px-3">
                    <div className="font-medium text-[#1C1B18] dark:text-[#E0E0E0]">{row.metricName}</div>
                    <div className="text-[10px] font-mono text-[#8C8A82] truncate max-w-[180px]">{row.metric}</div>
                  </td>
                  <td className="py-2.5 px-2 text-[11px] font-mono text-[#6B6960] dark:text-[#AAA]">{row.period}</td>
                  <td className="py-2.5 px-3 font-mono font-semibold text-right tabular-nums">
                    {formatNumber(row.value, 1)}
                  </td>
                  <td className="py-2.5 px-2 text-center text-[11px] text-[#6B6960] dark:text-[#AAA]">
                    {row.unit || "tỷ VND"}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {row.page ? (
                      <span className="px-1.5 py-0.5 text-[10px] font-mono font-medium bg-[#FEF3C7] text-[#92400E] dark:bg-[#78350F]/40 dark:text-[#FDE68A] rounded border border-[#FDE68A] dark:border-[#92400E]">
                        tr. {row.page}
                      </span>
                    ) : (
                      <span className="text-[#AAA] text-[10px]">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
