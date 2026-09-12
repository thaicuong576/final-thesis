import { Sparkles } from 'lucide-react';
import type { OrchestratorEntry as OrchestratorEntryType } from '../model/types';

interface OrchestratorEntryProps {
  entry: OrchestratorEntryType;
}

export function OrchestratorEntry({ entry }: OrchestratorEntryProps) {
  return (
    <div className="flex gap-3.5 items-start">
      <div className="w-8 h-8 rounded-full bg-[#edf7f3] border border-[#bce2d3] flex items-center justify-center shrink-0 mt-0.5 text-[#2f6f5e]">
        <Sparkles className="w-4 h-4" aria-hidden="true" />
      </div>

      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-ink">{entry.senderLabel}</span>
          <span className="text-[11px] text-muted">Tác tử điều phối quy trình</span>
        </div>

        <div className="bg-white border border-line rounded-lg p-3.5 text-sm text-ink leading-relaxed shadow-surface">
          {entry.message}
        </div>
      </div>
    </div>
  );
}
