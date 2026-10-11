import React, { useState } from "react";
import { X, FileText, TableProperties, Milestone, Loader2 } from "lucide-react";
import { DocumentTab } from "./DocumentTab";
import { DataTab } from "./DataTab";
import { JourneyTab } from "./JourneyTab";
import { useLineage } from "./useLineage";
import type { SourceDrawerProps, LineageTab } from "./types";

export const SourceDrawer: React.FC<SourceDrawerProps> = ({
  isOpen,
  onClose,
  noteNo,
  factId,
  observationId,
  report,
  defaultTab = "document",
}) => {
  const [selectedTab, setSelectedTab] = useState<LineageTab | null>(null);
  const [prevTargetKey, setPrevTargetKey] = useState<string>(
    `${noteNo}-${factId}-${defaultTab}`
  );

  const currentTargetKey = `${noteNo}-${factId}-${defaultTab}`;
  if (prevTargetKey !== currentTargetKey) {
    setPrevTargetKey(currentTargetKey);
    setSelectedTab(null);
  }

  const activeTab = selectedTab ?? defaultTab;
  const setActiveTab = setSelectedTab;

  const {
    node,
    isLoading,
    activeNote,
    activeFact,
    activeSentence,
    auditVerdict,
  } = useLineage({
    observationId,
    factId,
    noteNo,
    report,
  });

  if (!isOpen) return null;

  const entity = node?.entity || activeFact?.entity_id || "VCB";
  const metricName = node?.metric_name || activeFact?.metric_id || "Chỉ số tài chính";
  const period = node?.period || activeFact?.period || "2024_Q4";

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-2xs transition-opacity animate-in fade-in duration-200"
      aria-modal="true"
      role="dialog"
    >
      {/* Backdrop click to close */}
      <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />

      {/* Drawer content surface */}
      <div
        className="relative z-10 flex flex-col w-full sm:w-[580px] lg:w-[640px] h-full bg-[#FBFBFA] dark:bg-[#1C1B18] border-l border-[#E5E3DC] dark:border-[#333] shadow-xl animate-in slide-in-from-right duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 bg-white dark:bg-[#1E1E1E] border-b border-[#E5E3DC] dark:border-[#333] flex items-start justify-between gap-3 shrink-0">
          <div className="space-y-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 text-xs font-bold font-mono bg-[#B45309] text-white rounded">
                {entity}
              </span>
              <h3 className="text-base font-bold text-[#1C1B18] dark:text-[#F0F0F0] truncate">
                {metricName}
              </h3>
            </div>
            <p className="text-xs text-[#6B6960] dark:text-[#A0A0A0] flex items-center gap-2">
              <span>Kỳ công bố: {period}</span>
              {noteNo != null && (
                <>
                  <span>•</span>
                  <span className="font-medium text-[#B45309] dark:text-[#F59E0B]">
                    Chú thích [{noteNo}]
                  </span>
                </>
              )}
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-[#6B6960] hover:text-[#1C1B18] dark:hover:text-white rounded-md hover:bg-[#F4F3EF] dark:hover:bg-[#2C2C2C] transition-colors"
            aria-label="Đóng ngăn chi tiết"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab navigation bar */}
        <div
          role="tablist"
          aria-label="Các góc nhìn nguồn gốc số liệu"
          className="px-5 bg-white dark:bg-[#1E1E1E] border-b border-[#E5E3DC] dark:border-[#333] flex gap-2 shrink-0"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "document"}
            onClick={() => setActiveTab("document")}
            className={`flex items-center gap-1.5 py-2.5 px-3 text-xs font-medium border-b-2 transition-colors ${
              activeTab === "document"
                ? "border-[#B45309] text-[#B45309] dark:text-[#F59E0B] font-semibold"
                : "border-transparent text-[#6B6960] dark:text-[#999] hover:text-[#1C1B18]"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Tài liệu
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "data"}
            onClick={() => setActiveTab("data")}
            className={`flex items-center gap-1.5 py-2.5 px-3 text-xs font-medium border-b-2 transition-colors ${
              activeTab === "data"
                ? "border-[#B45309] text-[#B45309] dark:text-[#F59E0B] font-semibold"
                : "border-transparent text-[#6B6960] dark:text-[#999] hover:text-[#1C1B18]"
            }`}
          >
            <TableProperties className="w-3.5 h-3.5" />
            Dữ liệu
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "journey"}
            onClick={() => setActiveTab("journey")}
            className={`flex items-center gap-1.5 py-2.5 px-3 text-xs font-medium border-b-2 transition-colors ${
              activeTab === "journey"
                ? "border-[#B45309] text-[#B45309] dark:text-[#F59E0B] font-semibold"
                : "border-transparent text-[#6B6960] dark:text-[#999] hover:text-[#1C1B18]"
            }`}
          >
            <Milestone className="w-3.5 h-3.5" />
            Hành trình
          </button>
        </div>

        {/* Main Tab Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {isLoading && !node ? (
            <div className="flex flex-col items-center justify-center h-48 space-y-2 text-[#8C8A82]">
              <Loader2 className="w-6 h-6 animate-spin text-[#B45309]" />
              <span className="text-xs">Đang tải nguồn gốc và dữ liệu thẩm định...</span>
            </div>
          ) : (
            <>
              {activeTab === "document" && (
                <DocumentTab node={node} activeNote={activeNote} />
              )}
              {activeTab === "data" && (
                <DataTab node={node} activeFact={activeFact} />
              )}
              {activeTab === "journey" && (
                <JourneyTab
                  node={node}
                  activeFact={activeFact}
                  activeNote={activeNote}
                  activeSentence={activeSentence}
                  auditVerdict={auditVerdict}
                  onSelectTab={setActiveTab}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
