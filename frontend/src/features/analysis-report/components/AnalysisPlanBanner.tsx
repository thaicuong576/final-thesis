import { AlertCircle, CheckCircle2, Info, Layers, Network } from 'lucide-react';
import type { AnalysisPlan, BoundedRevisionSummary } from '../model/types';

interface AnalysisPlanBannerProps {
  plan: AnalysisPlan;
  revisionSummary?: BoundedRevisionSummary;
  limitations?: string[];
}

const CAPABILITY_LABELS: Record<string, string> = {
  company: 'Phân tích sức khỏe tài chính doanh nghiệp',
  sector: 'Đối chuẩn trung vị ngành',
  macro: 'Chính sách tiền tệ vĩ mô'
};

const LINK_LABELS: Record<string, string> = {
  peer_comparison: 'Đối chuẩn nhóm ngân hàng tương đồng',
  macro_transmission: 'Truyền dẫn chính sách tiền tệ',
  cross_level_stress: 'Kiểm tra sức chịu đựng liên tầng'
};

export function AnalysisPlanBanner({
  plan,
  revisionSummary,
  limitations = []
}: AnalysisPlanBannerProps) {
  const allLimitations = [
    ...(plan.known_limitations || []),
    ...limitations
  ];

  return (
    <section className="border border-line bg-card rounded-lg p-4 space-y-3 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-2.5">
        <div className="flex items-center gap-2">
          <Layers className="size-4 text-ink-secondary" aria-hidden="true" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-ink">
            Kế hoạch phân tích
          </h2>
        </div>

        {revisionSummary && (
          <div className="flex items-center gap-1.5 text-xs text-ink-secondary font-mono">
            <CheckCircle2 className="size-3.5 text-[#2d6a4f]" aria-hidden="true" />
            <span>
              Thẩm định: {revisionSummary.rounds_executed}/{revisionSummary.max_rounds} vòng (
              {revisionSummary.status === 'passed'
                ? 'Phê duyệt ngay'
                : revisionSummary.status === 'revised_and_passed'
                ? 'Đã hiệu đính'
                : revisionSummary.status}
              )
            </span>
          </div>
        )}
      </div>

      <p className="text-xs text-ink leading-relaxed font-normal">
        {plan.rationale}
      </p>

      {/* Execution Constraints Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1 text-xs">
        {/* Active capabilities */}
        <div className="border border-line rounded bg-surface-secondary p-2.5 space-y-1.5">
          <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-ink-secondary flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-amber" aria-hidden="true" />
            Năng lực phân tích kích hoạt ({plan.required_capabilities.length})
          </span>
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {plan.required_capabilities.map((cap) => (
              <span
                key={cap}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-card border border-border text-[11px] font-medium text-ink"
              >
                {CAPABILITY_LABELS[cap] || cap}
              </span>
            ))}
          </div>
        </div>

        {/* Applicable Links */}
        <div className="border border-line rounded bg-surface-secondary p-2.5 space-y-1.5">
          <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-ink-secondary flex items-center gap-1.5">
            <Network className="size-3 text-ink-secondary" aria-hidden="true" />
            Liên kết suy luận áp dụng ({plan.applicable_links.length})
          </span>
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {plan.applicable_links.length > 0 ? (
              plan.applicable_links.map((link) => (
                <span
                  key={link}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-card border border-border text-[11px] font-medium text-ink"
                >
                  {LINK_LABELS[link] || link}
                </span>
              ))
            ) : (
              <span className="text-[11px] text-ink-tertiary italic">
                Không có liên kết chéo (phân tích độc lập)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Limitations note if present */}
      {allLimitations.length > 0 ? (
        <div className="border border-amber-border/40 bg-amber-soft/30 rounded p-2.5 flex items-start gap-2 text-xs text-ink">
          <AlertCircle className="size-3.5 text-amber-border shrink-0 mt-0.5" aria-hidden="true" />
          <div className="space-y-0.5">
            <span className="font-semibold">Giới hạn phạm vi đã ghi nhận:</span>
            <ul className="list-disc list-inside text-ink-secondary text-[11px] space-y-0.5">
              {allLimitations.map((lim, idx) => (
                <li key={idx}>{lim}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 text-[11px] text-ink-tertiary">
          <Info className="size-3 shrink-0" aria-hidden="true" />
          <span>Không có giới hạn phương pháp luận trong phạm vi phân tích này.</span>
        </div>
      )}
    </section>
  );
}
