import React, { useState, useEffect } from "react";
import { apiFetch } from "@/shared/api/apiClient";
import { SourceDrawer } from "./SourceDrawer";
import { formatNumber, formatPeriod, formatUnit } from "./formatters";
import { formatDisplayText } from "@/shared/lib/formatting";
import type { LineageTab, ReportItem, SourceNoteItem, FactItem } from "./types";
import er9T01Fixture from "./fixtures/er9-t01-response.json";
import er9T07Fixture from "./fixtures/er9-t07-response.json";

export const SourceLineageDemo: React.FC = () => {
  const queryParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
  const initialReport = queryParams?.get("report") === "trend" ? "trend" : "ranking";
  const initialTab = (queryParams?.get("tab") as LineageTab) || "document";
  const initialObsId =
    queryParams?.get("obs") ||
    (initialReport === "trend"
      ? "observation-a36148537b6fbb8997d4a915bd689c74af6486a69b98ee6a655a841e03dc9ba8"
      : "observation-3a26e363c78be87d85d2c7b3a34d4121cc5b718647425d8b3017678fb966e936");
  const initialFactId =
    queryParams?.get("fact") ||
    (initialReport === "trend"
      ? "fact:value:VCB:2026_Q2:bank.roe"
      : "fact:value:VCB:2026_Q2:bank.llr_coverage");

  const [reportType, setReportType] = useState<"ranking" | "trend">(initialReport);
  const [isOpen, setIsOpen] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<LineageTab>(initialTab);
  const [selectedNoteNo, setSelectedNoteNo] = useState<number>(1);
  const [selectedFactId, setSelectedFactId] = useState<string | undefined>(initialFactId);
  const [selectedObsId, setSelectedObsId] = useState<string | undefined>(initialObsId);
  const [vcbLlrLabel, setVcbLlrLabel] = useState<string>("Bao phủ nợ xấu (LLR)");

  useEffect(() => {
    let active = true;
    apiFetch("/api/lineage/observation-3a26e363c78be87d85d2c7b3a34d4121cc5b718647425d8b3017678fb966e936")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (active && data && data.value != null) {
          const formatted = formatNumber(data.value, 1);
          setVcbLlrLabel(`Bao phủ nợ xấu: ${formatted}%`);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const activeReport = (
    reportType === "ranking" ? er9T01Fixture : er9T07Fixture
  ) as unknown as ReportItem;

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
              Dữ liệu thực từ API BCTC Quý 2/2026, Công thức tính toán và Hành trình truy nguyên 7 bước
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
                  setSelectedFactId("fact:value:VCB:2026_Q2:bank.llr_coverage");
                  setSelectedObsId(
                    "observation-3a26e363c78be87d85d2c7b3a34d4121cc5b718647425d8b3017678fb966e936"
                  );
                  setIsOpen(true);
                }}
                className={`px-3 py-1 font-medium rounded transition-colors cursor-pointer ${
                  reportType === "ranking"
                    ? "bg-white dark:bg-[#1E1E1E] text-[#B45309] font-semibold shadow-2xs"
                    : "text-[#6B6960] hover:text-[#1C1B18]"
                }`}
              >
                Báo cáo Quý 2/2026 (LLR Coverage)
              </button>
              <button
                type="button"
                id="btn-report-trend"
                onClick={() => {
                  setReportType("trend");
                  setSelectedNoteNo(1);
                  setSelectedFactId("fact:value:VCB:2026_Q2:bank.roe");
                  setSelectedObsId(
                    "observation-a36148537b6fbb8997d4a915bd689c74af6486a69b98ee6a655a841e03dc9ba8"
                  );
                  setIsOpen(true);
                }}
                className={`px-3 py-1 font-medium rounded transition-colors cursor-pointer ${
                  reportType === "trend"
                    ? "bg-white dark:bg-[#1E1E1E] text-[#B45309] font-semibold shadow-2xs"
                    : "text-[#6B6960] hover:text-[#1C1B18]"
                }`}
              >
                Báo cáo Xếp hạng ROE (Quý 4/2025)
              </button>
            </div>

            {/* Tab Selector */}
            <div className="flex rounded-md border border-[#E5E3DC] dark:border-[#444] bg-[#F4F3EF] dark:bg-[#252525] p-0.5 text-xs">
              <button
                type="button"
                id="btn-tab-document"
                onClick={() => setActiveTab("document")}
                className={`px-2.5 py-1 font-medium rounded transition-colors cursor-pointer ${
                  activeTab === "document"
                    ? "bg-white dark:bg-[#1E1E1E] text-[#B45309] font-semibold shadow-2xs"
                    : "text-[#6B6960] hover:text-[#1C1B18]"
                }`}
              >
                Tài liệu
              </button>
              <button
                type="button"
                id="btn-tab-data"
                onClick={() => setActiveTab("data")}
                className={`px-2.5 py-1 font-medium rounded transition-colors cursor-pointer ${
                  activeTab === "data"
                    ? "bg-white dark:bg-[#1E1E1E] text-[#B45309] font-semibold shadow-2xs"
                    : "text-[#6B6960] hover:text-[#1C1B18]"
                }`}
              >
                Dữ liệu
              </button>
              <button
                type="button"
                id="btn-tab-journey"
                onClick={() => setActiveTab("journey")}
                className={`px-2.5 py-1 font-medium rounded transition-colors cursor-pointer ${
                  activeTab === "journey"
                    ? "bg-white dark:bg-[#1E1E1E] text-[#B45309] font-semibold shadow-2xs"
                    : "text-[#6B6960] hover:text-[#1C1B18]"
                }`}
              >
                Hành trình
              </button>
            </div>

            {/* Quick Open/Close Toggle */}
            <button
              type="button"
              id="btn-toggle-drawer"
              onClick={() => setIsOpen(!isOpen)}
              className="px-3 py-1.5 text-xs font-semibold rounded-md bg-[#B45309] text-white hover:bg-[#92400E] shadow-2xs transition-colors cursor-pointer"
            >
              {isOpen ? "Đóng ngăn nguồn" : "Mở ngăn nguồn"}
            </button>
          </div>
        </div>

        {/* Real Fact Demonstrators */}
        <div className="p-4 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-xs space-y-3">
          <h3 className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0]">
            Các chỉ tiêu thực tế trong cơ sở dữ liệu chấp thuận (Bấm để xem truy vết):
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
            <button
              type="button"
              id="btn-fact-vcb-llr"
              onClick={() => {
                setSelectedFactId("fact:value:VCB:2026_Q2:bank.llr_coverage");
                setSelectedObsId(
                  "observation-3a26e363c78be87d85d2c7b3a34d4121cc5b718647425d8b3017678fb966e936"
                );
                setSelectedNoteNo(1);
                setIsOpen(true);
              }}
              className="p-3 text-left rounded-md border border-[#D97706] bg-[#FEF3C7]/40 dark:bg-[#78350F]/20 hover:bg-[#FEF3C7] dark:hover:bg-[#78350F]/40 transition-all cursor-pointer"
            >
              <span className="text-[10px] font-bold font-mono text-[#B45309] block">
                VCB · Quý 2/2026
              </span>
              <span className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0] block mt-0.5">
                {vcbLlrLabel}
              </span>
              <span className="text-[10px] text-[#6B6960] dark:text-[#A0A0A0] block mt-1">
                Dự phòng (tr. 7) / Nợ xấu (tr. 30)
              </span>
            </button>

            <button
              type="button"
              id="btn-fact-bid-llr"
              onClick={() => {
                setSelectedFactId("fact:value:BID:2026_Q2:bank.llr_coverage");
                setSelectedObsId(undefined);
                setSelectedNoteNo(2);
                setIsOpen(true);
              }}
              className="p-3 text-left rounded-md border border-[#E5E3DC] dark:border-[#333] bg-[#FAF9F5] dark:bg-[#252525] hover:border-[#B45309] transition-all cursor-pointer"
            >
              <span className="text-[10px] font-bold font-mono text-[#B45309] block">
                BID · Quý 2/2026
              </span>
              <span className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0] block mt-0.5">
                Bao phủ nợ xấu (LLR)
              </span>
              <span className="text-[10px] text-[#6B6960] dark:text-[#A0A0A0] block mt-1">
                BCTC hợp nhất Quý 2/2026
              </span>
            </button>

            <button
              type="button"
              id="btn-fact-vcb-npl"
              onClick={() => {
                setSelectedFactId("fact:value:VCB:2026_Q2:bank.npl_g35");
                setSelectedObsId(undefined);
                setSelectedNoteNo(1);
                setIsOpen(true);
              }}
              className="p-3 text-left rounded-md border border-[#E5E3DC] dark:border-[#333] bg-[#FAF9F5] dark:bg-[#252525] hover:border-[#B45309] transition-all cursor-pointer"
            >
              <span className="text-[10px] font-bold font-mono text-[#B45309] block">
                VCB · Quý 2/2026
              </span>
              <span className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0] block mt-0.5">
                Tỷ lệ nợ xấu (nhóm 3–5)
              </span>
              <span className="text-[10px] text-[#6B6960] dark:text-[#A0A0A0] block mt-1">
                Thuyết minh chất lượng nợ
              </span>
            </button>

            <button
              type="button"
              id="btn-fact-median"
              onClick={() => {
                setSelectedFactId("fact:peer_median:sector:bank:2026_Q2:bank.llr_coverage");
                setSelectedObsId(undefined);
                setSelectedNoteNo(1);
                setIsOpen(true);
              }}
              className="p-3 text-left rounded-md border border-[#E5E3DC] dark:border-[#333] bg-[#FAF9F5] dark:bg-[#252525] hover:border-[#B45309] transition-all cursor-pointer"
            >
              <span className="text-[10px] font-bold font-mono text-[#6B6960] block">
                Ngành Ngân hàng · Quý 2/2026
              </span>
              <span className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0] block mt-0.5">
                Trung vị bao phủ nợ xấu
              </span>
              <span className="text-[10px] text-[#6B6960] dark:text-[#A0A0A0] block mt-1">
                Tổng hợp 10 ngân hàng khảo sát
              </span>
            </button>
          </div>
        </div>

        {/* Current Active Report View */}
        <div className="p-6 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-sm space-y-4">
          <div className="space-y-2 border-b border-[#E5E3DC] dark:border-[#333] pb-4">
            <span className="text-[11px] font-mono font-medium text-[#B45309] uppercase tracking-wider">
              {activeReport.question_type} report · {activeReport.report_id}
            </span>
            <h2 className="text-xl font-bold text-[#1C1B18] dark:text-[#F0F0F0]">
              {activeReport.synthesis_summary ||
                "Phân tích cấu trúc vốn và an toàn tài chính ngân hàng niêm yết"}
            </h2>
          </div>

          {/* Citations bar */}
          <div className="p-4 bg-[#FAF9F5] dark:bg-[#252525] border border-[#E5E3DC] dark:border-[#333] rounded-lg space-y-3">
            <h4 className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0]">
              Các chú thích nguồn công bố ({activeReport.source_notes?.length || 0}):
            </h4>
            <div className="flex flex-wrap gap-2">
              {activeReport.source_notes?.slice(0, 10).map((n: SourceNoteItem) => (
                <button
                  key={n.note_no}
                  type="button"
                  id={`btn-citation-${n.note_no}`}
                  onClick={() => {
                    setSelectedNoteNo(n.note_no);
                    setSelectedFactId(n.fact_ids?.[0]);
                    setSelectedObsId(undefined);
                    setIsOpen(true);
                  }}
                  className={`px-3 py-1.5 text-xs rounded-md border font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                    selectedNoteNo === n.note_no
                      ? "bg-[#FEF3C7] dark:bg-[#78350F] text-[#92400E] dark:text-[#FDE68A] border-[#D97706] font-semibold"
                      : "bg-white dark:bg-[#1E1E1E] text-[#1C1B18] dark:text-[#E0E0E0] border-[#E5E3DC] dark:border-[#444] hover:border-[#B45309]"
                  }`}
                >
                  <span className="font-bold font-mono">[{n.note_no}]</span>
                  <span className="truncate max-w-[200px]">{n.title}</span>
                  {n.page && (
                    <span className="text-[10px] text-[#8C8A82]">
                      (tr. {n.page})
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Facts list */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0]">
              Sự kiện tài chính trong báo cáo (Bấm vào để mở nguồn gốc):
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {activeReport.facts?.slice(0, 6).map((f: FactItem, idx: number) => (
                <button
                  key={f.fact_id + idx}
                  type="button"
                  id={`btn-fact-${idx}`}
                  onClick={() => {
                    setSelectedFactId(f.fact_id);
                    setSelectedObsId(f.input_observation_ids?.[0]);
                    setSelectedNoteNo(1);
                    setIsOpen(true);
                  }}
                  className="p-2.5 text-left bg-[#FBFBFA] dark:bg-[#252525] border border-[#E5E3DC] dark:border-[#333] hover:border-[#B45309] rounded-md transition-colors cursor-pointer"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-[#B45309]">
                      {f.entity_id || "Ngành"}
                    </span>
                    <span className="font-mono text-[11px] text-[#6B6960]">
                      {formatPeriod(f.period)}
                    </span>
                  </div>
                  <div className="text-xs text-[#1C1B18] dark:text-[#E0E0E0] mt-1 font-medium truncate">
                    {formatDisplayText(f.metric_id)}
                  </div>
                  {f.value != null && (
                    <div className="text-xs font-bold text-[#1C1B18] dark:text-[#F0F0F0] mt-0.5 font-mono">
                      {formatNumber(f.value, 1)} {formatUnit(f.unit)}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Standalone Source Drawer (LIN-1) */}
      <SourceDrawer
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        noteNo={selectedNoteNo}
        factId={selectedFactId}
        observationId={selectedObsId}
        report={activeReport}
        defaultTab={activeTab}
      />
    </div>
  );
};
