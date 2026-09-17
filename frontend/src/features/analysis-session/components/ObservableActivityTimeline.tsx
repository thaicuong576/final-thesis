import { Database, CheckCircle2, Sparkles, RefreshCw } from 'lucide-react';
import type { ObservableActivity } from '../model/types';

interface ObservableActivityTimelineProps {
  activities: ObservableActivity[];
  title?: string;
  hideHeader?: boolean;
}

export function ObservableActivityTimeline({
  activities,
  title = 'Hoạt động quan sát được',
  hideHeader = false
}: ObservableActivityTimelineProps) {
  const getActivityIcon = (type: ObservableActivity['type']) => {
    switch (type) {
      case 'DATA_RETRIEVAL':
        return <Database className="w-3.5 h-3.5 text-muted" aria-hidden="true" />;
      case 'VALIDATION':
        return <CheckCircle2 className="w-3.5 h-3.5 text-[#2f6f5e]" aria-hidden="true" />;
      case 'INSIGHT_GENERATION':
        return <Sparkles className="w-3.5 h-3.5 text-[#0066cc]" aria-hidden="true" />;
      case 'REVISION':
        return <RefreshCw className="w-3.5 h-3.5 text-[#b47d14]" aria-hidden="true" />;
    }
  };

  const getActivityTypeLabel = (type: ObservableActivity['type']) => {
    switch (type) {
      case 'DATA_RETRIEVAL':
        return 'Truy xuất dữ liệu';
      case 'VALIDATION':
        return 'Kiểm tra tính hợp lệ';
      case 'INSIGHT_GENERATION':
        return 'Tạo nhận định';
      case 'REVISION':
        return 'Hiệu chỉnh';
    }
  };

  return (
    <div className="space-y-2.5">
      {!hideHeader && (
        <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
          {title}
        </h3>
      )}

      <div className="space-y-2 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-px before:bg-line">
        {activities.map((act) => (
          <div key={act.id} className="flex items-start gap-3 relative z-10">
            <div className="w-7 h-7 rounded-full bg-white border border-line flex items-center justify-center shrink-0 mt-0.5">
              {getActivityIcon(act.type)}
            </div>

            <div className="flex-1 bg-white border border-line rounded-lg p-2.5 shadow-surface">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">
                  {getActivityTypeLabel(act.type)}
                </span>
                {act.timestamp && (
                  <span className="text-[10px] text-muted">{act.timestamp}</span>
                )}
              </div>
              <p className="text-xs text-ink leading-relaxed font-medium">
                {act.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
