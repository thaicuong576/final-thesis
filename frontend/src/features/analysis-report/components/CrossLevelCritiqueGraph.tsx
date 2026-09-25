import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  FileCheck,
  GitBranch,
  Sparkles
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { formatMetric } from '@/shared/lib/formatting';
import type { AtomicClaim, ClaimType, CritiqueItem } from '../model/types';

interface CrossLevelCritiqueGraphProps {
  crossLevelCritique: CritiqueItem[];
  atomicClaims: AtomicClaim[];
  linkableEvidenceIds?: Set<string>;
  onSelectEvidence?: (evidenceId: string) => void;
  selectedEvidenceId?: string | null;
}

const CLAIM_TYPE_LABELS: Record<ClaimType, { label: string; variant: string }> = {
  peer_comparison: { label: 'Đối chuẩn ngành', variant: 'bg-surface-secondary text-ink' },
  factual_observation: { label: 'Quan sát thực tế', variant: 'bg-card text-ink' },
  policy_transmission: { label: 'Truyền dẫn chính sách', variant: 'bg-amber-soft text-ink' },
  synthesis_evaluation: { label: 'Đánh giá tổng hợp', variant: 'bg-surface-secondary text-ink' }
};

export function CrossLevelCritiqueGraph({
  crossLevelCritique,
  atomicClaims,
  linkableEvidenceIds = new Set(),
  onSelectEvidence,
  selectedEvidenceId
}: CrossLevelCritiqueGraphProps) {
  const [expandedClaimIds, setExpandedClaimIds] = useState<Set<string>>(
    new Set(atomicClaims.map((c) => c.claim_id))
  );

  const toggleClaimExpand = (claimId: string) => {
    setExpandedClaimIds((prev) => {
      const next = new Set(prev);
      if (next.has(claimId)) {
        next.delete(claimId);
      } else {
        next.add(claimId);
      }
      return next;
    });
  };

  return (
    <section className="border border-line bg-card rounded-lg p-5 space-y-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-3">
        <div className="flex items-center gap-2">
          <GitBranch className="size-4 text-ink-secondary" aria-hidden="true" />
          <h2 className="text-sm font-bold tracking-tight text-ink">
            Luận điểm phân tích và phản biện
          </h2>
        </div>

        <div className="text-xs text-ink-secondary font-mono">
          <span>{atomicClaims.length} khẳng định do API trả về</span>
        </div>
      </div>

      {/* Part A: Cross-Level Critique Findings (Only if critique items exist) */}
      {crossLevelCritique.length > 0 && (
        <div className="space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-ink-secondary">
            <Sparkles className="size-3.5 text-amber-border" aria-hidden="true" />
            <span>Phát hiện phản biện tương quan liên tầng</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {crossLevelCritique.map((item, idx) => (
              <div
                key={idx}
                className="border border-line rounded-md bg-surface-secondary p-3.5 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-ink truncate pr-2">
                    {item.dimension}
                  </span>
                  <span className="font-mono text-[11px] font-bold px-1.5 py-0.5 rounded bg-card border border-border text-[#1b4332]">
                    Độ tin cậy {item.confidence != null && !isNaN(Number(item.confidence)) ? formatMetric(item.confidence * 100, 1) : 'N/A'}
                  </span>
                </div>

                <p className="text-xs text-ink leading-relaxed font-normal">
                  {item.finding}
                </p>

                {item.evidence_ref && (
                  <div className="pt-1 flex items-center gap-1.5 text-[11px] font-mono text-ink-tertiary">
                    <span>Tham chiếu bằng chứng:</span>
                    <span className="text-ink font-semibold bg-card px-1.5 py-0.5 rounded border border-border">
                      {item.evidence_ref}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Part B: Atomic Claims Graph */}
      <div className="space-y-3 pt-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-ink-secondary">
            <FileCheck className="size-3.5 text-[#2d6a4f]" aria-hidden="true" />
            <span>Các luận điểm trong phản hồi API</span>
          </div>
          <span className="text-[11px] font-mono text-ink-tertiary">
            Trạng thái và bằng chứng hiển thị theo phản hồi API
          </span>
        </div>

        <div className="space-y-2.5">
          {atomicClaims.map((claim) => {
            const isExpanded = expandedClaimIds.has(claim.claim_id);
            const typeInfo =
              CLAIM_TYPE_LABELS[claim.claim_type] || {
                label: claim.claim_type,
                variant: 'bg-surface-secondary text-ink'
              };

            return (
              <div
                key={claim.claim_id}
                className="border border-line rounded-md bg-surface-primary p-3.5 space-y-2.5 hover:border-border-strong transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-ink bg-surface-secondary px-2 py-0.5 rounded border border-border">
                      {claim.claim_id}
                    </span>

                    <Badge
                      variant="outline"
                      className={`text-[10px] font-semibold border-border ${typeInfo.variant}`}
                    >
                      {typeInfo.label}
                    </Badge>

                    <Badge variant="outline" className="text-[10px] font-mono border-border bg-surface-secondary text-ink-secondary">
                      Stage 1: {claim.stage1_status === 'accepted'
                        ? 'accepted'
                        : claim.stage1_status === 'rejected'
                        ? 'rejected'
                        : 'chưa công bố'}
                    </Badge>

                    <Badge
                      variant="outline"
                      className={`text-[10px] font-mono gap-1 ${
                        claim.stage2_critique_status === 'revised'
                          ? 'bg-amber-soft text-ink border-amber-border/70 font-semibold'
                          : 'bg-surface-secondary text-ink-secondary border-border'
                      }`}
                    >
                      Phản biện: {claim.stage2_critique_status || 'chưa công bố'}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-ink-secondary">
                      Độ tin cậy:{' '}
                      <strong className="text-ink">
                        {claim.confidence != null && !isNaN(Number(claim.confidence)) ? formatMetric(claim.confidence * 100, 1) : 'N/A'}
                      </strong>
                    </span>

                    <button
                      type="button"
                      onClick={() => toggleClaimExpand(claim.claim_id)}
                      className="p-1 rounded text-ink-tertiary hover:text-ink hover:bg-surface-hover"
                      aria-label={isExpanded ? 'Thu gọn bằng chứng' : 'Mở rộng bằng chứng'}
                    >
                      {isExpanded ? (
                        <ChevronUp className="size-4" aria-hidden="true" />
                      ) : (
                        <ChevronDown className="size-4" aria-hidden="true" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Statement text */}
                <p className="text-xs sm:text-sm font-medium text-ink leading-relaxed">
                  {claim.statement}
                </p>

                {/* Evidence References Pill List */}
                {isExpanded && (
                  <div className="border-t border-line/60 pt-2 flex flex-wrap items-center gap-2 text-xs">
                    <span className="text-[11px] font-mono text-ink-tertiary">
                      Neo bằng chứng ({claim.evidence_refs.length}):
                    </span>
                    {claim.evidence_refs.map((refId) => {
                      const isSelected = selectedEvidenceId === refId;
                      return linkableEvidenceIds.has(refId) ? (
                        <button
                          key={refId}
                          type="button"
                          onClick={() => onSelectEvidence?.(refId)}
                          className={`font-mono text-[11px] px-2 py-0.5 rounded border transition-colors ${
                            isSelected
                              ? 'bg-amber text-ink font-bold border-amber-border'
                              : 'bg-surface-secondary text-ink-secondary hover:text-ink hover:bg-surface-hover border-border'
                          }`}
                        >
                          #{refId}
                        </button>
                      ) : (
                        <span key={refId} className="font-mono text-[11px] px-2 py-0.5 rounded border border-border bg-surface-secondary text-ink-secondary">
                          #{refId}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
