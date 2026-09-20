import { Database, ArrowLeft } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { OrchestratorPhase } from '../model/types';

interface SessionContextBarProps {
  datasetName: string;
  scopeSignature: string;
  currentPhase: OrchestratorPhase;
  phaseLabel: string;
  onBackToComposer?: () => void;
  connectionBadge?: React.ReactNode;
}

export function SessionContextBar({
  datasetName,
  scopeSignature,
  currentPhase,
  phaseLabel,
  onBackToComposer,
  connectionBadge
}: SessionContextBarProps) {
  const getBadgeStyle = (phase: OrchestratorPhase) => {
    switch (phase) {
      case 'READY_FOR_REPORT':
        return 'bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3]';
      case 'BLOCKED':
        return 'bg-[#fef2f2] text-[#991b1b] border-[#fecaca]';
      case 'REVISING':
        return 'bg-[#fef9ee] text-[#b47d14] border-[#f5dfaa]';
      case 'REVIEWING':
      case 'SYNTHESIZING':
        return 'bg-[#f0f7ff] text-[#0066cc] border-[#b8daff]';
      default:
        return 'bg-canvas text-muted border-line';
    }
  };

  return (
    <div className="border border-line bg-white rounded-lg p-4 shadow-surface">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <Database className="w-3.5 h-3.5 text-muted" aria-hidden="true" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
              Phiên phân tích đa tác tử
            </span>
            <Badge
              variant="outline"
              className={`gap-1 px-2 py-0.5 text-[11px] font-medium ${getBadgeStyle(
                currentPhase
              )}`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  currentPhase === 'READY_FOR_REPORT'
                    ? 'bg-[#2f6f5e]'
                    : currentPhase === 'BLOCKED'
                    ? 'bg-[#dc2626]'
                    : currentPhase === 'REVISING'
                    ? 'bg-[#b47d14] animate-pulse'
                    : 'bg-[#0066cc]'
                }`}
                aria-hidden="true"
              />
              {phaseLabel}
            </Badge>
            {connectionBadge}
          </div>


          <div className="flex flex-wrap items-center gap-x-2 text-sm">
            <span className="font-semibold text-ink">{datasetName}</span>
            <span className="text-muted" aria-hidden="true">•</span>
            <span className="font-medium text-muted">{scopeSignature}</span>
          </div>
        </div>

        {onBackToComposer && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onBackToComposer}
            className="self-start sm:self-auto border-line text-xs font-medium text-ink hover:bg-canvas gap-1.5 h-8"
          >
            <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
            Chỉnh sửa câu hỏi
          </Button>
        )}
      </div>
    </div>
  );
}
