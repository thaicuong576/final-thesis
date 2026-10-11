import React, { useState } from "react";
import { ExternalLink, FileText, AlertCircle, RefreshCw } from "lucide-react";
import type { LineageNode, SourceNoteItem } from "./types";

interface DocumentTabProps {
  node: LineageNode | null;
  activeNote?: SourceNoteItem | null;
}

interface LeafItem {
  id: string;
  metric: string;
  metricName: string;
  value?: number | null;
  unit?: string | null;
  title: string;
  url: string;
  page: number;
  section?: string | null;
  rowLabel?: string | null;
  reading?: string | null;
}

export const DocumentTab: React.FC<DocumentTabProps> = ({ node, activeNote }) => {
  const [iframeError, setIframeError] = useState(false);

  // Extract all leaf nodes with a URL and page
  const leaves: LeafItem[] = [];

  function collectLeaves(curr: LineageNode | null) {
    if (!curr) return;
    if (curr.children && curr.children.length > 0) {
      for (const child of curr.children) {
        collectLeaves(child);
      }
    } else {
      const url = curr.source_url || activeNote?.url || "";
      const page = curr.page || activeNote?.page || 1;
      leaves.push({
        id: curr.observation_id,
        metric: curr.metric,
        metricName: curr.metric_name || curr.metric,
        value: curr.value,
        unit: curr.unit,
        title: curr.source_title || activeNote?.title || "Báo cáo tài chính",
        url,
        page,
        section: curr.section,
        rowLabel: curr.row_label,
        reading: curr.reading,
      });
    }
  }

  collectLeaves(node);

  // If no leaves found, synthesize from note
  if (leaves.length === 0 && (activeNote || node)) {
    const url = activeNote?.url || node?.source_url || "";
    const page = activeNote?.page || node?.page || 1;
    leaves.push({
      id: "leaf-fallback",
      metric: node?.metric || "Chỉ tiêu",
      metricName: node?.metric_name || "Chỉ tiêu tài chính",
      value: node?.value,
      unit: node?.unit,
      title: activeNote?.title || node?.source_title || "Báo cáo tài chính",
      url,
      page,
      section: node?.section || activeNote?.locator,
      rowLabel: node?.row_label || "Chỉ tiêu công bố",
      reading: node?.reading || "single",
    });
  }

  const [selectedIndex, setSelectedIndex] = useState(0);
  const activeLeaf = leaves[selectedIndex] || leaves[0];

  const formatNumber = (num?: number | null) => {
    if (num == null) return "—";
    return num.toLocaleString("vi-VN", { maximumFractionDigits: 2 });
  };

  const leafUrl = activeLeaf?.url;
  const leafPage = activeLeaf?.page || 1;
  const embedUrl = leafUrl ? `${leafUrl}#page=${leafPage}` : "";

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Multiple leaves selector if more than 1 leaf */}
      {leaves.length > 1 && (
        <div className="flex flex-wrap gap-1.5 p-1.5 bg-[#F4F3EF] dark:bg-[#252525] rounded-md border border-[#E5E3DC] dark:border-[#333]">
          {leaves.map((leaf, idx) => (
            <button
              key={leaf.id + idx}
              type="button"
              onClick={() => {
                setSelectedIndex(idx);
                setIframeError(false);
              }}
              className={`px-2.5 py-1 text-xs font-medium rounded transition-colors ${
                selectedIndex === idx
                  ? "bg-white dark:bg-[#1E1E1E] text-[#1C1B18] dark:text-[#E0E0E0] shadow-xs font-semibold border border-[#D5D3CC] dark:border-[#444]"
                  : "text-[#6B6960] dark:text-[#A0A0A0] hover:text-[#1C1B18] hover:bg-white/50"
              }`}
            >
              {leaf.metricName || `Nguồn ${idx + 1}`} (tr. {leaf.page})
            </button>
          ))}
        </div>
      )}

      {/* Primary Evidence Header Card */}
      <div className="p-3 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-2xs space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#B45309] shrink-0" />
              <h4 className="text-sm font-semibold text-[#1C1B18] dark:text-[#F0F0F0] truncate">
                {activeLeaf?.title || "Báo cáo tài chính"}
              </h4>
              <span className="px-1.5 py-0.5 text-[11px] font-mono font-medium bg-[#FEF3C7] text-[#92400E] dark:bg-[#78350F]/40 dark:text-[#FDE68A] rounded border border-[#FDE68A] dark:border-[#92400E]">
                Trang {leafPage}
              </span>
            </div>
            {activeLeaf?.section && (
              <p className="text-xs text-[#6B6960] dark:text-[#A0A0A0] mt-0.5 truncate">
                {activeLeaf.section}
              </p>
            )}
          </div>

          {leafUrl ? (
            <a
              href={embedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-[#B45309] dark:text-[#F59E0B] bg-[#FFFBEB] dark:bg-[#451A03] hover:bg-[#FEF3C7] border border-[#FDE68A] dark:border-[#78350F] rounded transition-colors shrink-0"
            >
              Mở tab mới
              <ExternalLink className="w-3 h-3" />
            </a>
          ) : null}
        </div>

        {/* Fact values row */}
        <div className="pt-2 border-t border-[#F0EFEA] dark:border-[#2A2A2A] grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-[#8C8A82] dark:text-[#888] block text-[11px]">Dòng trích xuất BCTC:</span>
            <span className="font-medium text-[#1C1B18] dark:text-[#E0E0E0] truncate block">
              {activeLeaf?.rowLabel || "Toàn bộ báo cáo / chỉ tiêu tính toán"}
            </span>
          </div>
          <div>
            <span className="text-[#8C8A82] dark:text-[#888] block text-[11px]">Giá trị ghi nhận:</span>
            <span className="font-mono font-semibold text-[#1C1B18] dark:text-[#E0E0E0]">
              {formatNumber(activeLeaf?.value)} {activeLeaf?.unit || ""}
            </span>
          </div>
        </div>

        {activeLeaf?.reading && (
          <div className="flex items-center gap-2 pt-1 text-[11px] text-[#6B6960] dark:text-[#999]">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>Phương thức đọc: {activeLeaf.reading === "confirmed_ocr_twice" ? "Đối soát kép OCR" : activeLeaf.reading}</span>
          </div>
        )}
      </div>

      {/* Embedded PDF Viewer / Fallback Frame */}
      <div className="flex-1 min-h-[380px] bg-[#F4F3EF] dark:bg-[#1A1A1A] border border-[#E5E3DC] dark:border-[#333] rounded-lg overflow-hidden relative flex flex-col">
        {leafUrl && !iframeError ? (
          <iframe
            src={embedUrl}
            title={`BCTC Viewer - Trang ${leafPage}`}
            className="w-full h-full min-h-[420px] flex-1 border-0"
            onError={() => setIframeError(true)}
          />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center space-y-3 bg-[#FAF9F5] dark:bg-[#202020]">
            <AlertCircle className="w-10 h-10 text-[#D97706]" />
            <div className="max-w-md space-y-1">
              <h5 className="text-sm font-semibold text-[#1C1B18] dark:text-[#F0F0F0]">
                Chính sách bảo mật trang công bố thông tin
              </h5>
              <p className="text-xs text-[#6B6960] dark:text-[#A0A0A0] leading-relaxed">
                Máy chủ công bố thông tin gốc ({activeLeaf?.title}) chặn nhúng khung iframe trên trình duyệt của bạn hoặc yêu cầu kết nối trực tiếp.
              </p>
            </div>

            {leafUrl ? (
              <a
                href={embedUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-[#D97706] hover:bg-[#B45309] rounded-md shadow-xs transition-colors"
              >
                Mở tài liệu tại trang {leafPage} trong tab mới
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            ) : (
              <p className="text-xs text-rose-600 font-medium">Chưa có liên kết URL khả dụng cho tài liệu này.</p>
            )}

            {iframeError && (
              <button
                type="button"
                onClick={() => setIframeError(false)}
                className="inline-flex items-center gap-1 text-[11px] text-[#6B6960] hover:text-[#1C1B18] dark:hover:text-white"
              >
                <RefreshCw className="w-3 h-3" /> Thử tải lại khung nhúng
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
