import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Building2, Users, Globe, CheckCircle2, RefreshCw } from 'lucide-react';
import type { SpecialistSessionState, SpecialistStatus } from '../model/types';
import { ObservableActivityTimeline } from './ObservableActivityTimeline';
import { SpecialistArtifactSummaryBlock } from './SpecialistArtifactSummaryBlock';
import { ReviewFeedbackBlock } from './ReviewFeedbackBlock';
import { RevisionRoundBlock } from './RevisionRoundBlock';

interface SpecialistSessionSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  session?: SpecialistSessionState | null;
  invocation?: SpecialistSessionState | null; // Compatibility alias
}

export function SpecialistSessionSheet({
  open,
  onOpenChange,
  session,
  invocation: legacyInvocation
}: SpecialistSessionSheetProps) {
  const currentSession = session || legacyInvocation;

  if (!currentSession) {
    return null;
  }

  const getSpecialistIcon = () => {
    switch (currentSession.specialistId) {
      case 'company':
        return <Building2 className="w-4 h-4 text-ink" aria-hidden="true" />;
      case 'peer':
        return <Users className="w-4 h-4 text-ink" aria-hidden="true" />;
      case 'macro':
        return <Globe className="w-4 h-4 text-ink" aria-hidden="true" />;
    }
  };

  const getStatusBadge = (status: SpecialistStatus, label: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <Badge
            variant="outline"
            className="bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3] gap-1 px-2 py-0.5 text-xs font-semibold"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-[#2f6f5e]" aria-hidden="true" />
            {label}
          </Badge>
        );
      case 'OUTPUT_CREATED':
        return (
          <Badge
            variant="outline"
            className="bg-[#edf7f3] text-[#2f6f5e] border-[#bce2d3] gap-1 px-2 py-0.5 text-xs font-semibold"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-[#2f6f5e]" aria-hidden="true" />
            {label}
          </Badge>
        );
      case 'REVISING':
        return (
          <Badge
            variant="outline"
            className="bg-[#fef9ee] text-[#b47d14] border-[#f5dfaa] gap-1 px-2 py-0.5 text-xs font-semibold"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[#b47d14] animate-spin" aria-hidden="true" />
            {label}
          </Badge>
        );
      case 'ANALYZING':
      case 'REVIEWING':
        return (
          <Badge
            variant="outline"
            className="bg-[#f0f7ff] text-[#0066cc] border-[#b8daff] gap-1 px-2 py-0.5 text-xs font-semibold"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#0066cc] animate-pulse" aria-hidden="true" />
            {label}
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="bg-canvas text-muted border-line text-xs">
            {label}
          </Badge>
        );
    }
  };

  const hasMultipleArtifacts = currentSession.artifactHistory.length > 1;
  const initialArtifact = currentSession.artifactHistory[0] || currentSession.artifact;
  const revisedArtifact = hasMultipleArtifacts
    ? currentSession.artifactHistory[currentSession.artifactHistory.length - 1]
    : null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto p-6 space-y-6">
        <SheetHeader className="space-y-3 pb-4 border-b border-line text-left">
          <div className="flex items-center justify-between gap-3 pr-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#f1f5f9] flex items-center justify-center shrink-0">
                {getSpecialistIcon()}
              </div>
              <SheetTitle className="text-base font-semibold text-ink">
                {currentSession.label}
              </SheetTitle>
            </div>
            {getStatusBadge(currentSession.status, currentSession.statusLabel)}
          </div>

          <SheetDescription className="text-xs text-muted leading-relaxed">
            Phiên làm việc và tiến trình kiểm chứng độc lập của tác tử chuyên môn.
          </SheetDescription>
        </SheetHeader>

        {/* Section 1: Assigned task */}
        <div className="space-y-1.5 bg-[#fafafa] border border-line rounded-lg p-3.5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
            Nhiệm vụ được phân công
          </span>
          <p className="text-xs text-ink font-medium leading-relaxed">
            {currentSession.assignment}
          </p>
        </div>

        {/* Section 2: Initial Artifact (v1) if available */}
        {initialArtifact && (
          <div className="space-y-2">
            {hasMultipleArtifacts && (
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
                Kết quả ban đầu (v1)
              </span>
            )}
            <SpecialistArtifactSummaryBlock artifact={initialArtifact} />
          </div>
        )}

        {/* Section 3: Review Feedback from Orchestrator (if present) */}
        {currentSession.review && (
          <ReviewFeedbackBlock review={currentSession.review} />
        )}

        {/* Section 4: Targeted Revision Progress (if present) */}
        {currentSession.revision && (
          <RevisionRoundBlock revision={currentSession.revision} />
        )}

        {/* Section 5: Revised Artifact (v2) if present */}
        {revisedArtifact && (
          <div className="space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#2f6f5e]">
              Kết quả sau hiệu chỉnh (v2)
            </span>
            <SpecialistArtifactSummaryBlock artifact={revisedArtifact} />
          </div>
        )}

        {/* Section 6: Observable Activities Timeline */}
        {currentSession.activities.length > 0 && (
          <ObservableActivityTimeline activities={currentSession.activities} />
        )}
      </SheetContent>
    </Sheet>
  );
}
