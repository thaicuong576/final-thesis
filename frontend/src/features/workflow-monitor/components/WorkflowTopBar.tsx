import type { WorkflowRun, DemoScenarioId } from '../model/types';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Database, Clock, Activity } from 'lucide-react';
import { Link } from 'react-router-dom';

interface WorkflowTopBarProps {
  workflowRun: WorkflowRun;
  activeScenarioId: DemoScenarioId;
  onSelectScenario: (scenarioId: DemoScenarioId) => void;
}

export function WorkflowTopBar({
  workflowRun,
  activeScenarioId,
  onSelectScenario
}: WorkflowTopBarProps) {
  const { question, scopeSignature, datasetName, orchestrator } = workflowRun;

  const statusConfig = {
    PREPARING: { bg: 'bg-[#f0f4f8]', text: 'text-muted', border: 'border-line', label: 'Đang chuẩn bị' },
    RUNNING: { bg: 'bg-[#ebf3fb]', text: 'text-[#1c5d9c]', border: 'border-[#b8d5f2]', label: 'Đang phân tích' },
    REVISING: { bg: 'bg-[#fff8eb]', text: 'text-[#9a6700]', border: 'border-[#fde0a3]', label: 'Đang hiệu chỉnh' },
    SYNTHESIZING: { bg: 'bg-[#f3f0fc]', text: 'text-[#5d3ebc]', border: 'border-[#d7c9f8]', label: 'Đang tổng hợp' },
    READY_FOR_REPORT: { bg: 'bg-[#edf7f3]', text: 'text-[#2f6f5e]', border: 'border-[#bce2d3]', label: 'Sẵn sàng tạo báo cáo' }
  }[orchestrator.overallStatus] || {
    bg: 'bg-[#ebf3fb]',
    text: 'text-[#1c5d9c]',
    border: 'border-[#b8d5f2]',
    label: orchestrator.overallStatusLabel
  };

  return (
    <div className="space-y-4">
      {/* Upper subnav with prototype scenario switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-line">
        <Link
          to="/analysis"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Quay lại khung phân tích mới</span>
        </Link>

        {/* Prototype scenario switcher for defense and evaluation */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-semibold text-muted uppercase tracking-wider mr-1">
            Kịch bản kiểm thử:
          </span>
          {[
            { id: 'COMPANY_ONLY' as const, label: 'A. Doanh nghiệp' },
            { id: 'COMPANY_PEER' as const, label: 'B. Doanh nghiệp + Đối sánh' },
            { id: 'TARGETED_REVISION' as const, label: 'C. Hiệu chỉnh tập trung' },
            { id: 'BROAD_ANALYSIS' as const, label: 'D. Toàn diện' }
          ].map((sc) => (
            <button
              key={sc.id}
              type="button"
              onClick={() => onSelectScenario(sc.id)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition border ${
                activeScenarioId === sc.id
                  ? 'bg-[#1c5d9c] text-white border-[#1c5d9c]'
                  : 'bg-white text-muted hover:text-ink border-line hover:border-slate-400'
              }`}
            >
              {sc.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Anchor Card */}
      <div className="bg-white border border-line rounded-xl p-5 shadow-surface space-y-3">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-1.5 min-w-0">
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="font-bold text-ink uppercase tracking-wider text-[11px]">
                Quy trình phân tích đa tác tử
              </span>
              <span className="text-muted" aria-hidden="true">•</span>
              <span className="inline-flex items-center gap-1 text-muted">
                <Database className="w-3 h-3" />
                <span>{datasetName}</span>
              </span>
              <span className="text-muted" aria-hidden="true">•</span>
              <span className="inline-flex items-center gap-1 text-muted">
                <Clock className="w-3 h-3" />
                <span>Khởi tạo lúc 09:20</span>
              </span>
            </div>

            <h1 className="text-base sm:text-lg font-bold text-ink leading-snug">
              “{question}”
            </h1>

            <div className="flex items-center gap-2 text-xs text-muted">
              <span className="font-semibold text-ink">Phạm vi xác thực:</span>
              <span className="font-medium text-[#1c5d9c]">{scopeSignature}</span>
            </div>
          </div>

          <div className="self-start md:self-center shrink-0">
            <Badge
              variant="outline"
              className={`${statusConfig.bg} ${statusConfig.text} ${statusConfig.border} gap-1.5 px-3 py-1 text-xs font-semibold`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>{statusConfig.label}</span>
            </Badge>
          </div>
        </div>
      </div>
    </div>
  );
}
