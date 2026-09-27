import { Sparkles, AlertCircle } from 'lucide-react';
import type { OrchestratorMessageEntry } from '../model/types';
import { Badge } from '@/components/ui/badge';

interface OrchestratorEntryProps {
  entry: OrchestratorMessageEntry;
}

export function OrchestratorEntry({ entry }: OrchestratorEntryProps) {
  const isBlocked = entry.phase === 'BLOCKED';

  return (
    <div className="flex gap-3.5 items-start">
      <div
        className={`w-8 h-8 rounded-full border flex items-center justify-center shrink-0 mt-0.5 ${
          isBlocked
            ? 'bg-blocked-soft border-blocked/30 text-blocked'
            : 'bg-[#edf7f3] border-[#bce2d3] text-[#2f6f5e]'
        }`}
      >
        {isBlocked ? (
          <AlertCircle className="w-4 h-4" aria-hidden="true" />
        ) : (
          <Sparkles className="w-4 h-4" aria-hidden="true" />
        )}
      </div>

      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-ink">{entry.senderLabel}</span>
          <span className="text-[11px] text-muted">Tác tử điều phối quy trình</span>
          {isBlocked && (
            <Badge
              variant="outline"
              className="bg-blocked-soft text-blocked border-blocked/30 text-[10px] font-semibold"
            >
              Cần điều chỉnh yêu cầu
            </Badge>
          )}
        </div>

        <div
          className={`border rounded-lg p-3.5 text-sm leading-relaxed shadow-surface ${
            isBlocked
              ? 'bg-blocked-soft/20 border-blocked/30 text-ink'
              : 'bg-white border-line text-ink'
          }`}
        >
          {entry.message}
        </div>
      </div>
    </div>
  );
}
