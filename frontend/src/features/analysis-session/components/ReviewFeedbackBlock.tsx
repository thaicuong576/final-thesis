import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { ReviewFeedback } from '../model/types';

interface ReviewFeedbackBlockProps {
  review: ReviewFeedback;
}

export function ReviewFeedbackBlock({ review }: ReviewFeedbackBlockProps) {
  const isPending = review.status === 'PENDING_REVISION';

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
          Đánh giá từ Điều phối viên
        </h3>
        <Badge
          variant="outline"
          className={`text-[10px] font-semibold px-2 py-0.5 gap-1 ${
            isPending
              ? 'bg-[#fef9ee] text-[#b47d14] border-[#f5dfaa]'
              : 'bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3]'
          }`}
        >
          {isPending ? (
            <>
              <AlertTriangle className="w-3 h-3 text-[#b47d14]" aria-hidden="true" />
              Yêu cầu hiệu chỉnh
            </>
          ) : (
            <>
              <CheckCircle2 className="w-3 h-3 text-[#2f6f5e]" aria-hidden="true" />
              Đã khắc phục
            </>
          )}
        </Badge>
      </div>

      <div
        className={`border rounded-lg p-3.5 space-y-1.5 ${
          isPending
            ? 'bg-[#fffdfa] border-[#f5dfaa]'
            : 'bg-[#fafcfb] border-[#bce2d3]'
        }`}
      >
        <div className="flex items-center gap-1.5 text-xs font-semibold text-ink">
          <span>Người đánh giá:</span>
          <span className="text-[#2f6f5e]">{review.reviewer}</span>
        </div>
        <p className="text-xs text-ink leading-relaxed font-medium">
          {review.critiqueSummary}
        </p>
      </div>
    </div>
  );
}
