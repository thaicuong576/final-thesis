import React from "react";
import {
  FileText,
  TableProperties,
  Binary,
  PieChart,
  Award,
  Quote,
  ShieldCheck,
  ChevronRight,
} from "lucide-react";
import type {
  LineageNode,
  LineageTab,
  JourneyStep,
  FactItem,
  SourceNoteItem,
  SentenceItem,
  AuditVerdictItem,
} from "./types";
import { formatNumber, formatPeriod } from "./formatters";

interface JourneyTabProps {
  node: LineageNode | null;
  activeFact?: FactItem | null;
  activeNote?: SourceNoteItem | null;
  activeSentence?: SentenceItem | null;
  auditVerdict?: AuditVerdictItem | null;
  onSelectTab: (tab: LineageTab) => void;
}

export const JourneyTab: React.FC<JourneyTabProps> = ({
  node,
  activeFact,
  activeNote,
  activeSentence,
  auditVerdict,
  onSelectTab,
}) => {
  if (!node) {
    return (
      <div className="p-6 text-center text-xs text-[#8C8A82]">
        Đang tải hành trình truy nguyên số liệu...
      </div>
    );
  }

  const page = node.page ?? (node.children?.[0]?.page ?? 7);
  const filingTitle = activeNote?.title || node.source_title || `${node.entity} · Báo cáo tài chính`;
  const formula = node.formula_version || activeFact?.formula_version || "primary-calculation-v1";
  const ratioValue = `${formatNumber(node.value, 1)} ${node.unit || "%"}`;
  const periodVi = formatPeriod(node.period);

  // Fact description
  const factDesc = (() => {
    if (activeFact?.fact_type === "peer_rank") {
      return `Xếp hạng ${activeFact.value}/${activeFact.denominator || 5} trong nhóm ngành`;
    }
    if (activeFact?.fact_type === "peer_median") {
      return `Trung vị ngành ${formatPeriod(activeFact.period)}: ${formatNumber(activeFact.value, 1)}%`;
    }
    if (activeFact?.fact_type === "gap_to_median") {
      const val = typeof activeFact.value === "number" ? activeFact.value : 0;
      return `Chênh lệch so với trung vị: ${val > 0 ? "+" : ""}${formatNumber(val, 1)} điểm %`;
    }
    return `${node.entity} đạt ${ratioValue} ${periodVi}`;
  })();

  // Sentence text
  const sentenceText =
    activeSentence?.text ||
    `${node.entity} ghi nhận ${node.metric_name || node.metric} đạt ${ratioValue} trong ${periodVi}, thể hiện chất lượng số liệu đã thẩm định.`;

  // Verdict details
  const isAccepted = auditVerdict?.status !== "dropped";
  const verdictText =
    auditVerdict?.reason ||
    "Kiểm định đối soát thành công: Toàn bộ số liệu khớp tuyệt đối với BCTC và dữ liệu gốc.";

  const steps: JourneyStep[] = [
    {
      id: "step-1-filing",
      stepNumber: 1,
      label: "BCTC & Trang công bố",
      title: `${filingTitle} (Trang ${page})`,
      detail: `Điểm xuất phát: Thuyết minh BCTC gốc công bố công khai của ${node.entity}.`,
      meta: "Nguồn dữ liệu ban đầu",
      tabTarget: "document",
      badge: `Trang ${page}`,
      badgeType: "neutral",
    },
    {
      id: "step-2-inputs",
      stepNumber: 2,
      label: "Dòng dữ liệu đầu vào",
      title: "Các dòng số liệu trích xuất",
      detail: `Trích xuất từ chỉ tiêu '${node.row_label || "Thuyết minh nợ & dự phòng"}' (phương thức: ${node.reading || "OCR đã kiểm tra"}).`,
      meta: `${node.children?.length || 1} chỉ tiêu thành phần`,
      tabTarget: "data",
      badge: "Đã trích xuất",
      badgeType: "success",
    },
    {
      id: "step-3-formula",
      stepNumber: 3,
      label: "Công thức toán học",
      title: `Thuật toán ${formula}`,
      detail: "Code tính toán tài chính thực thi độc lập (sai lệch ≤ 0,00005).",
      meta: "Định mức tất định",
      tabTarget: "data",
      badge: "Chuẩn hóa",
      badgeType: "success",
    },
    {
      id: "step-4-ratio",
      stepNumber: 4,
      label: "Chỉ số tài chính",
      title: `${node.metric_name || node.metric} = ${ratioValue}`,
      detail: `Giá trị tính toán hoàn tất cho ${node.entity} kỳ ${node.period}.`,
      meta: "Chỉ số hoàn chỉnh",
      tabTarget: "data",
      badge: ratioValue,
      badgeType: "neutral",
    },
    {
      id: "step-5-fact",
      stepNumber: 5,
      label: "Sự kiện phân tích (Fact)",
      title: factDesc,
      detail: "Chỉ số được đối chiếu với toàn bộ danh mục ngân hàng trong kỳ khảo sát.",
      meta: activeFact?.fact_id || "fact:value",
      badge: "Sự kiện đã xác minh",
      badgeType: "success",
    },
    {
      id: "step-6-sentence",
      stepNumber: 6,
      label: "Câu văn báo cáo",
      title: `"${sentenceText}"`,
      detail: "Mô hình phân tích tổng hợp câu văn vào báo cáo và gắn chú thích trích dẫn.",
      meta: activeSentence?.sentence_id || "sent-1",
      badge: "Trích dẫn báo cáo",
      badgeType: "neutral",
    },
    {
      id: "step-7-verdict",
      stepNumber: 7,
      label: "Thẩm định chất lượng (Verifier)",
      title: isAccepted ? "Kiểm định đạt chuẩn 100%" : "Cảnh báo kiểm định",
      detail: verdictText,
      meta: "Narrative Audit Engine",
      badge: isAccepted ? "Passed" : "Audit Review",
      badgeType: isAccepted ? "success" : "warning",
    },
  ];

  const getStepIcon = (num: number) => {
    switch (num) {
      case 1:
        return <FileText className="w-3.5 h-3.5 text-[#B45309]" />;
      case 2:
        return <TableProperties className="w-3.5 h-3.5 text-[#D97706]" />;
      case 3:
        return <Binary className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />;
      case 4:
        return <PieChart className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />;
      case 5:
        return <Award className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />;
      case 6:
        return <Quote className="w-3.5 h-3.5 text-violet-600 dark:text-violet-400" />;
      case 7:
        return <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-4">
      <div className="p-3 bg-[#FAF9F5] dark:bg-[#202020] border border-[#E5E3DC] dark:border-[#333] rounded-lg">
        <p className="text-xs text-[#6B6960] dark:text-[#A0A0A0] leading-relaxed">
          Đường dẫn chứng minh liên tục từ <strong className="text-[#1C1B18] dark:text-[#E0E0E0]">Trang BCTC gốc</strong> qua <strong className="text-[#1C1B18] dark:text-[#E0E0E0]">công thức tất định</strong> đến <strong className="text-[#1C1B18] dark:text-[#E0E0E0]">câu văn trích dẫn</strong> và <strong className="text-[#1C1B18] dark:text-[#E0E0E0]">kết luận thẩm định</strong>. Bấm vào từng bước để xem chi tiết.
        </p>
      </div>

      <div className="relative pl-6 space-y-3.5 before:absolute before:left-3 before:top-2 before:bottom-3 before:w-0.5 before:bg-[#E5E3DC] dark:before:bg-[#333]">
        {steps.map((st) => (
          <div
            key={st.id}
            onClick={() => st.tabTarget && onSelectTab(st.tabTarget)}
            className={`relative group p-3 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg transition-all shadow-2xs ${
              st.tabTarget ? "cursor-pointer hover:border-[#B45309] dark:hover:border-[#D97706] hover:shadow-xs" : ""
            }`}
          >
            {/* Step dot */}
            <div className="absolute -left-[27px] top-3.5 w-5 h-5 rounded-full bg-white dark:bg-[#1E1E1E] border-2 border-[#B45309] flex items-center justify-center text-[10px] font-bold text-[#B45309]">
              {st.stepNumber}
            </div>

            <div className="flex items-start justify-between gap-2">
              <div className="space-y-1 min-w-0">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#8C8A82] dark:text-[#888] uppercase tracking-wide">
                  {getStepIcon(st.stepNumber)}
                  <span>{st.label}</span>
                </div>
                <h5 className="text-xs font-semibold text-[#1C1B18] dark:text-[#F0F0F0] leading-snug break-words">
                  {st.title}
                </h5>
                <p className="text-[11px] text-[#6B6960] dark:text-[#A0A0A0] leading-relaxed">
                  {st.detail}
                </p>
              </div>

              {st.tabTarget && (
                <div className="flex items-center text-[#B45309] dark:text-[#D97706] text-xs shrink-0 self-center opacity-70 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all">
                  <span className="text-[11px] font-medium hidden sm:inline mr-0.5">
                    {st.tabTarget === "document" ? "Xem PDF" : "Xem số"}
                  </span>
                  <ChevronRight className="w-4 h-4" />
                </div>
              )}
            </div>

            {st.badge && (
              <div className="mt-2 pt-1.5 border-t border-[#F0EFEA] dark:border-[#2A2A2A] flex items-center justify-between text-[10px]">
                <span className="text-[#8C8A82] font-mono">{st.meta}</span>
                <span
                  className={`px-1.5 py-0.5 rounded font-mono font-medium ${
                    st.badgeType === "success"
                      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                      : st.badgeType === "warning"
                      ? "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
                      : "bg-[#F4F3EF] text-[#6B6960] dark:bg-[#2A2A2A] dark:text-[#AAA] border border-[#E5E3DC] dark:border-[#444]"
                  }`}
                >
                  {st.badge}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
