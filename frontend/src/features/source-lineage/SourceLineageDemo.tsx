import React, { useState } from "react";
import { SourceDrawer } from "./SourceDrawer";
import type { LineageTab, ReportItem, SourceNoteItem, FactItem } from "./types";
import rankingFixture from "@/test/fixtures/er-ranking-coverage-2024q4.json";
import trendFixture from "@/test/fixtures/er-trend-vpb-roe-2024.json";

export const SourceLineageDemo: React.FC = () => {
  const [reportType, setReportType] = useState<"ranking" | "trend">("ranking");
  const [isOpen, setIsOpen] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<LineageTab>("document");
  const [selectedNoteNo, setSelectedNoteNo] = useState<number>(1);
  const [selectedFactId, setSelectedFactId] = useState<string | undefined>(undefined);

  const activeReport = (reportType === "ranking" ? rankingFixture : trendFixture) as unknown as ReportItem;

  return (
    <div className="min-h-screen bg-[#F4F3EF] dark:bg-[#121212] p-6 text-[#1C1B18] dark:text-[#E0E0E0] font-sans">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Top Control Header */}
        <div className="p-4 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-xs flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-base font-bold text-[#1C1B18] dark:text-[#F0F0F0]">
              Kiểm thử & Trình diễn Ngăn Nguồn gốc Số liệu (Source Drawer Harness)
            </h1>
            <p className="text-xs text-[#6B6960] dark:text-[#A0A0A0]">
              Minh chứng BCTC, Công thức toán học và Hành trình truy nguyên 7 bước
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Report Selector */}
            <div className="flex rounded-md border border-[#E5E3DC] dark:border-[#444] bg-[#F4F3EF] dark:bg-[#252525] p-0.5 text-xs">
              <button
                type="button"
                id="btn-report-ranking"
                onClick={() => {
                  setReportType("ranking");
                  setSelectedNoteNo(1);
                  setSelectedFactId(undefined);
                }}
                className={`px-3 py-1 font-medium rounded ${
                  reportType === "ranking"
                    ? "bg-white dark:bg-[#1E1E1E] text-[#B45309] font-semibold shadow-2xs"
                    : "text-[#6B6960] hover:text-[#1C1B18]"
                }`}
              >
                Báo cáo Xếp hạng (LLR)
              </button>
              <button
                type="button"
                id="btn-report-trend"
                onClick={() => {
                  setReportType("trend");
                  setSelectedNoteNo(1);
                  setSelectedFactId(undefined);
                }}
                className={`px-3 py-1 font-medium rounded ${
                  reportType === "trend"
                    ? "bg-white dark:bg-[#1E1E1E] text-[#B45309] font-semibold shadow-2xs"
                    : "text-[#6B6960] hover:text-[#1C1B18]"
                }`}
              >
                Báo cáo Xu hướng (ROE)
              </button>
            </div>

            {/* Tab direct selector */}
            <div className="flex rounded-md border border-[#E5E3DC] dark:border-[#444] bg-[#F4F3EF] dark:bg-[#252525] p-0.5 text-xs">
              <button
                type="button"
                id="btn-tab-document"
                onClick={() => setActiveTab("document")}
                className={`px-2.5 py-1 font-medium rounded ${
                  activeTab === "document"
                    ? "bg-white dark:bg-[#1E1E1E] text-[#B45309] font-semibold shadow-2xs"
                    : "text-[#6B6960]"
                }`}
              >
                Tài liệu
              </button>
              <button
                type="button"
                id="btn-tab-data"
                onClick={() => setActiveTab("data")}
                className={`px-2.5 py-1 font-medium rounded ${
                  activeTab === "data"
                    ? "bg-white dark:bg-[#1E1E1E] text-[#B45309] font-semibold shadow-2xs"
                    : "text-[#6B6960]"
                }`}
              >
                Dữ liệu
              </button>
              <button
                type="button"
                id="btn-tab-journey"
                onClick={() => setActiveTab("journey")}
                className={`px-2.5 py-1 font-medium rounded ${
                  activeTab === "journey"
                    ? "bg-white dark:bg-[#1E1E1E] text-[#B45309] font-semibold shadow-2xs"
                    : "text-[#6B6960]"
                }`}
              >
                Hành trình
              </button>
            </div>

            <button
              type="button"
              id="btn-toggle-drawer"
              onClick={() => setIsOpen(!isOpen)}
              className="px-3 py-1 text-xs font-semibold text-white bg-[#B45309] hover:bg-[#92400E] rounded shadow-xs"
            >
              {isOpen ? "Ẩn Ngăn" : "Mở Ngăn"}
            </button>
          </div>
        </div>

        {/* Report Preview Body */}
        <div className="p-6 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-xs space-y-6">
          <div className="space-y-2 border-b border-[#E5E3DC] dark:border-[#333] pb-4">
            <span className="text-[11px] font-mono font-medium text-[#B45309] uppercase tracking-wider">
              {activeReport.question_type} report · {activeReport.report_id}
            </span>
            <h2 className="text-xl font-bold text-[#1C1B18] dark:text-[#F0F0F0]">
              {activeReport.synthesis_summary}
            </h2>
          </div>

          {/* Citations bar */}
          <div className="p-4 bg-[#FAF9F5] dark:bg-[#252525] border border-[#E5E3DC] dark:border-[#333] rounded-lg space-y-3">
            <h4 className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0]">
              Các chú thích nguồn công bố ({activeReport.source_notes?.length || 0}):
            </h4>
            <div className="flex flex-wrap gap-2">
              {activeReport.source_notes?.map((n: SourceNoteItem) => (
                <button
                  key={n.note_no}
                  type="button"
                  id={`btn-citation-${n.note_no}`}
                  onClick={() => {
                    setSelectedNoteNo(n.note_no);
                    setSelectedFactId(n.fact_ids?.[0]);
                    setIsOpen(true);
                  }}
                  className={`px-3 py-1.5 text-xs rounded-md border font-medium flex items-center gap-1.5 transition-all ${
                    selectedNoteNo === n.note_no
                      ? "bg-[#FEF3C7] dark:bg-[#78350F] text-[#92400E] dark:text-[#FDE68A] border-[#D97706] font-semibold"
                      : "bg-white dark:bg-[#1E1E1E] text-[#1C1B18] dark:text-[#E0E0E0] border-[#E5E3DC] dark:border-[#444] hover:border-[#B45309]"
                  }`}
                >
                  <span className="font-bold font-mono">[{n.note_no}]</span>
                  <span className="truncate max-w-[200px]">{n.title}</span>
                  {n.page && <span className="text-[10px] text-[#8C8A82]">(tr. {n.page})</span>}
                </button>
              ))}
            </div>
          </div>

          {/* Facts list */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0]">
              Sự kiện tài chính (Bấm vào chỉ tiêu để mở nguồn gốc):
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {activeReport.facts?.slice(0, 6).map((f: FactItem, idx: number) => (
                <button
                  key={f.fact_id + idx}
                  type="button"
                  id={`btn-fact-${idx}`}
                  onClick={() => {
                    setSelectedFactId(f.fact_id);
                    setSelectedNoteNo(1);
                    setIsOpen(true);
                  }}
                  className="p-2.5 text-left bg-[#FBFBFA] dark:bg-[#252525] border border-[#E5E3DC] dark:border-[#333] hover:border-[#B45309] rounded-md transition-colors"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-[#B45309]">{f.entity_id || "Ngành"}</span>
                    <span className="font-mono text-[11px] text-[#6B6960]">{f.period}</span>
                  </div>
                  <div className="text-xs font-semibold text-[#1C1B18] dark:text-[#E0E0E0] mt-1">
                    {f.fact_type === "peer_rank" ? `Hạng ${f.value}/${f.denominator}` : `${f.value} ${f.unit || ""}`}
                  </div>
                  <div className="text-[10px] font-mono text-[#8C8A82] truncate mt-0.5">
                    {f.fact_id}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* The Source Drawer */}
      <SourceDrawer
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        noteNo={selectedNoteNo}
        factId={selectedFactId}
        report={activeReport}
        defaultTab={activeTab}
      />
    </div>
  );
};
