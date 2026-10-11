import React from "react";
import { CheckCircle2, Calculator, Database, AlertTriangle } from "lucide-react";
import { formatNumber, formatPeriod, formatUnit, buildSubstitutedFormula } from "./formatters";
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

  // Flatten child nodes into table rows
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

  // Build formula display string strictly from receipt
  const receipt = node.calculation_receipt;
  const formulaName = receipt?.formula_version || node.formula_version || null;
  const substitutedFormula = buildSubstitutedFormula(receipt, node.value, node.unit);

  const receiptResult = receipt?.result || node.receipt_result || "passed";
  const tolerance = receipt?.tolerance || node.receipt_tolerance || "0,00005";

  // Check for value mismatch between activeFact and lineage root node
  const factVal = activeFact?.value;
  const rootVal = node.value;
  let hasMismatch = false;
  let mismatchMessage = "";

  if (
    factVal != null &&
    rootVal != null &&
    (activeFact?.fact_type === "value" || activeFact?.metric_id === node.metric)
  ) {
    // Normalize percentage scales if factVal is ratio (e.g. 2.79 vs 279.28)
    const scale =
      Math.abs(factVal - rootVal) > 10 && Math.abs(factVal * 100 - rootVal) < 2
        ? 100
        : 1;
    const normalizedFact = factVal * scale;
    const diff = Math.abs(normalizedFact - rootVal);
    const tolNumber = parseFloat(String(tolerance).replace(",", ".")) || 0.00005;

    if (diff > tolNumber) {
      hasMismatch = true;
      mismatchMessage = `Cảnh báo sai lệch: Số liệu sự kiện (${formatNumber(
        factVal,
        2
      )}) khác biệt so với số liệu truy nguyên gốc (${formatNumber(
        rootVal,
        2
      )}), chênh lệch ${formatNumber(diff, 5)} vượt quá ngưỡng sai lệch cho phép (${tolerance}).`;
    }
  }

  return (
    <div className="flex flex-col space-y-4">
      {/* Value Mismatch Warning */}
      {hasMismatch && (
        <div className="p-3.5 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700/60 rounded-lg flex items-start gap-2.5 text-amber-900 dark:text-amber-200 text-xs">
          <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold">Phát hiện sai lệch số liệu:</span>
            <p className="leading-relaxed">{mismatchMessage}</p>
          </div>
        </div>
      )}

      {/* Formula & Substitution Card */}
      {substitutedFormula ? (
        <div className="p-3.5 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-2xs space-y-2.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <Calculator className="w-4 h-4 text-[#B45309]" />
              <span className="text-xs font-semibold text-[#1C1B18] dark:text-[#F0F0F0]">
                Công thức & Số liệu thay thế
              </span>
            </div>
            {formulaName && (
              <span className="px-2 py-0.5 text-[11px] font-mono bg-[#F4F3EF] dark:bg-[#2A2A2A] text-[#6B6960] dark:text-[#AAA] rounded border border-[#E5E3DC] dark:border-[#444]">
                {formulaName}
              </span>
            )}
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
                Output: {receipt.calculated_output.slice(0, 10)}...
              </span>
            )}
          </div>
        </div>
      ) : (
        /* Direct Observation without formula receipt */
        <div className="p-3.5 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-2xs space-y-1.5">
          <div className="flex items-center gap-1.5 text-[#1C1B18] dark:text-[#F0F0F0]">
            <Database className="w-4 h-4 text-[#B45309]" />
            <span className="text-xs font-semibold">Chỉ số gốc công bố</span>
          </div>
          <div className="p-2.5 bg-[#FAF9F5] dark:bg-[#252525] border border-[#E5E3DC] dark:border-[#333] rounded font-mono text-sm font-semibold text-[#B45309]">
            {node.metric_name || node.metric} = {formatNumber(node.value, 2)}{" "}
            {formatUnit(node.unit)}
          </div>
          <p className="text-[11px] text-[#8C8A82]">
            Số liệu trích xuất trực tiếp từ báo cáo tài chính, không qua bước tính toán dẫn xuất.
          </p>
        </div>
      )}

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
            <tbody className="divide-y divide-[#E5E3DC] dark:divide-[#333]">
              {rows.map((r, i) => (
                <tr
                  key={r.metric + i}
                  className="hover:bg-[#FAF9F5] dark:hover:bg-[#222] transition-colors"
                >
                  <td className="py-2 px-3 font-bold font-mono text-[#B45309]">
                    {r.entity}
                  </td>
                  <td className="py-2 px-3 font-medium text-[#1C1B18] dark:text-[#E0E0E0]">
                    {r.metricName}
                  </td>
                  <td className="py-2 px-2 font-mono text-[11px] text-[#6B6960] dark:text-[#A0A0A0]">
                    {formatPeriod(r.period)}
                  </td>
                  <td className="py-2 px-3 text-right font-mono font-semibold text-[#1C1B18] dark:text-[#F0F0F0]">
                    {formatNumber(r.value, 1)}
                  </td>
                  <td className="py-2 px-2 text-center text-[#6B6960] dark:text-[#A0A0A0] text-[11px]">
                    {formatUnit(r.unit) || "—"}
                  </td>
                  <td className="py-2 px-3 text-center">
                    {r.page ? (
                      <span className="inline-block px-1.5 py-0.5 font-mono text-[10px] font-bold bg-[#FAF9F5] dark:bg-[#2A2A2A] text-[#B45309] rounded border border-[#E5E3DC] dark:border-[#444]">
                        tr. {r.page}
                      </span>
                    ) : (
                      <span className="text-[#8C8A82] text-[11px]">—</span>
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
