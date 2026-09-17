import { RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { RevisionRound } from '../model/types';
import { ObservableActivityTimeline } from './ObservableActivityTimeline';

interface RevisionRoundBlockProps {
  revision: RevisionRound;
}

export function RevisionRoundBlock({ revision }: RevisionRoundBlockProps) {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
          Quá trình hiệu chỉnh có chủ đích
        </h3>
        <Badge
          variant="outline"
          className="bg-[#fef9ee] text-[#b47d14] border-[#f5dfaa] text-[10px] font-semibold gap-1"
        >
          <RefreshCw className="w-3 h-3 text-[#b47d14]" aria-hidden="true" />
          Vòng {revision.round} / {revision.maxRounds}
        </Badge>
      </div>

      <div className="border border-[#f5dfaa] bg-[#fffdfa] rounded-lg p-3.5 space-y-3">
        <div>
          <span className="text-[11px] font-semibold text-muted uppercase tracking-wider">
            Mục tiêu hiệu chỉnh:
          </span>
          <p className="text-xs text-ink font-medium mt-0.5 leading-relaxed">
            {revision.reason}
          </p>
        </div>

        {revision.activities.length > 0 && (
          <div className="pt-2 border-t border-[#f7e6be]">
            <ObservableActivityTimeline
              activities={revision.activities}
              title="Hoạt động trong vòng hiệu chỉnh"
            />
          </div>
        )}
      </div>
    </div>
  );
}
