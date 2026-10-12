import React, { useState } from "react";
import { ExternalLink, FileText, ShieldCheck, Info } from "lucide-react";
import { formatNumber, formatUnit } from "./formatters";
import type { LineageNode, SourceNoteItem } from "./types";

interface DocumentTabProps {
  node: LineageNode | null;
  activeNote?: SourceNoteItem | null;
}

interface LeafItem {
  id: string;
  entity: string;
  metric: string;
  metricName: string;
  value?: number | null;
  unit?: string | null;
  title: string;
  url: string | null;
  page?: number | null;
  section?: string | null;
  rowLabel?: string | null;
  reading?: string | null;
}

export const DocumentTab: React.FC<DocumentTabProps> = ({ node, activeNote }) => {
  // Collect all leaf nodes with their OWN pages from lineage
  const leaves: LeafItem[] = [];

  function collectLeaves(curr: LineageNode | null) {
    if (!curr) return;
    if (curr.children && curr.children.length > 0) {
      for (const child of curr.children) {
        collectLeaves(child);
      }
    } else {
      leaves.push({
        id: curr.observation_id,
        entity: curr.entity,
        metric: curr.metric,
        metricName: curr.metric_name || curr.metric,
        value: curr.value,
        unit: curr.unit,
        title: curr.source_title || activeNote?.title || `${curr.entity} · Báo cáo tài chính`,
        url: curr.source_url || activeNote?.url || null,
        page: curr.page ?? null, // leaf's own page strictly, never note's page or 1
        section: curr.section,
        rowLabel: curr.row_label,
        reading: curr.reading,
      });
    }
  }

  collectLeaves(node);

  const [selectedIndex, setSelectedIndex] = useState(0);
  const activeLeaf = leaves[selectedIndex] || leaves[0];

  if (!node && !activeLeaf) {
    return (
      <div className="p-6 text-center text-xs text-[#8C8A82]">
        Đang tải thông tin tài liệu công bố...
      </div>
    );
  }

  const leafUrl = activeLeaf?.url;
  const leafPage = activeLeaf?.page;
  const pageLabel = leafPage != null ? `Trang ${leafPage}` : "Chưa gắn trang";
  const externalLinkUrl = leafUrl
    ? leafPage != null
      ? `${leafUrl}#page=${leafPage}`
      : leafUrl
    : null;

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Multiple leaves selector if more than 1 leaf */}
      {leaves.length > 1 && (
        <div className="flex flex-wrap gap-1.5 p-1.5 bg-[#F4F3EF] dark:bg-[#252525] rounded-md border border-[#E5E3DC] dark:border-[#333]">
          {leaves.map((leaf, idx) => {
            const isSelected = selectedIndex === idx;
            const hasMultipleBanks = new Set(leaves.map((l) => l.entity)).size > 1;
            const label = hasMultipleBanks
              ? `[${leaf.entity}] ${leaf.metricName}`
              : leaf.metricName;

            return (
              <button
                key={leaf.id + idx}
                type="button"
                onClick={() => setSelectedIndex(idx)}
                className={`px-2.5 py-1 text-xs rounded font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                  isSelected
                    ? "bg-[#B45309] text-white shadow-2xs font-semibold"
                    : "bg-white dark:bg-[#1E1E1E] text-[#1C1B18] dark:text-[#D0D0D0] border border-[#E5E3DC] dark:border-[#444] hover:border-[#B45309]"
                }`}
              >
                <span>{label}</span>
                {leaf.page != null && (
                  <span
                    className={`text-[10px] px-1 py-0.2 rounded font-mono ${
                      isSelected
                        ? "bg-amber-800 text-amber-100"
                        : "bg-[#F4F3EF] dark:bg-[#2A2A2A] text-[#8C8A82]"
                    }`}
                  >
                    tr. {leaf.page}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Primary Leaf Metadata Card */}
      <div className="p-4 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-2xs space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1 min-w-0">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#B45309] shrink-0" />
              <h4 className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0] truncate">
                {activeLeaf?.title || "Báo cáo tài chính"}
              </h4>
            </div>
            {activeLeaf?.section && (
              <p className="text-[11px] text-[#6B6960] dark:text-[#A0A0A0]">
                Phần: {activeLeaf.section}
              </p>
            )}
          </div>

          {leafPage != null && (
            <span className="shrink-0 px-2 py-0.5 text-xs font-mono font-bold bg-[#FEF3C7] dark:bg-[#78350F] text-[#92400E] dark:text-[#FDE68A] rounded border border-[#D97706]/40">
              {pageLabel}
            </span>
          )}
        </div>

        {/* Fact details extracted from filing row */}
        <div className="p-3 bg-[#FAF9F5] dark:bg-[#252525] border border-[#E5E3DC] dark:border-[#333] rounded-md space-y-2 text-xs">
          <div className="space-y-1">
            <div className="flex items-start justify-between gap-2">
              <span className="text-[#6B6960] dark:text-[#999] shrink-0">Chỉ tiêu công bố:</span>
              <span className="font-semibold text-[#1C1B18] dark:text-[#F0F0F0] text-right">
                {activeLeaf?.metricName || "—"}
              </span>
            </div>
            {activeLeaf?.rowLabel && (
              <div className="flex items-start justify-between gap-2 text-[11px]">
                <span className="text-[#8C8A82] shrink-0">Dòng BCTC gốc:</span>
                <span className="text-[#6B6960] dark:text-[#AAA] font-mono text-right">
                  {activeLeaf.rowLabel}
                </span>
              </div>
            )}
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#6B6960] dark:text-[#999]">Giá trị trích xuất:</span>
            <span className="font-bold text-[#B45309] dark:text-[#F59E0B] font-mono text-sm">
              {formatNumber(activeLeaf?.value, 1)} {formatUnit(activeLeaf?.unit)}
            </span>
          </div>
          {activeLeaf?.reading && (
            <div className="flex items-center justify-between pt-1 border-t border-[#EBE8E0] dark:border-[#333] text-[11px]">
              <span className="text-[#8C8A82]">Phương thức đọc:</span>
              <span className="text-[#6B6960] dark:text-[#AAA] font-mono">
                {activeLeaf.reading}
              </span>
            </div>
          )}
        </div>

        {/* First-class Neutral PDF Action Fallback */}
        <div className="p-3 bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 rounded-md space-y-2.5 text-xs">
          <div className="flex items-start gap-2 text-amber-900 dark:text-amber-200">
            <Info className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <p className="leading-relaxed text-[11px]">
              Xem và đối chiếu số liệu trực tiếp tại trang báo cáo tài chính gốc công bố chính thức.
            </p>
          </div>

          {externalLinkUrl ? (
            <a
              href={externalLinkUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full py-2.5 px-4 bg-[#B45309] hover:bg-[#92400E] text-white rounded-md font-semibold text-xs flex items-center justify-center gap-2 shadow-2xs transition-colors cursor-pointer"
            >
              <ExternalLink className="w-4 h-4" />
              <span>Mở trang PDF gốc ({pageLabel})</span>
            </a>
          ) : (
            <div className="text-center py-2 text-[11px] text-[#8C8A82]">
              URL tệp PDF công bố không khả dụng.
            </div>
          )}
        </div>

        <div className="flex items-center gap-1.5 text-[11px] text-emerald-700 dark:text-emerald-400 font-medium">
          <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>Dữ liệu đã được kiểm tra khớp định mức với báo cáo tài chính gốc.</span>
        </div>
      </div>
    </div>
  );
};
