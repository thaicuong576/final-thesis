import { FileCheck, ShieldCheck } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { SpecialistArtifactSummary } from '../model/types';

interface SpecialistArtifactSummaryBlockProps {
  artifact: SpecialistArtifactSummary;
}

export function SpecialistArtifactSummaryBlock({
  artifact
}: SpecialistArtifactSummaryBlockProps) {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
          Kết quả chuyên môn (Artifact)
        </h3>
        <Badge
          variant="outline"
          className="bg-canvas text-ink border-line text-[10px] font-semibold"
        >
          Phiên bản v{artifact.version}
        </Badge>
      </div>

      <div className="bg-[#fcfdfd] border border-[#bce2d3] rounded-lg p-3.5 space-y-3">
        <div className="flex items-center justify-between border-b border-[#e2efe9] pb-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-[#2f6f5e]">
            <FileCheck className="w-4 h-4" aria-hidden="true" />
            <span>{artifact.headline}</span>
          </div>

          <div className="flex items-center gap-1 text-[11px] text-muted">
            <ShieldCheck className="w-3.5 h-3.5 text-[#2f6f5e]" aria-hidden="true" />
            <span>{artifact.evidenceCount} dẫn chứng kiểm chứng</span>
          </div>
        </div>

        <ul className="space-y-2 text-xs text-ink">
          {artifact.findings.map((finding, idx) => (
            <li key={idx} className="flex items-start gap-2 leading-relaxed">
              <span className="w-1.5 h-1.5 rounded-full bg-[#2f6f5e] mt-1.5 shrink-0" aria-hidden="true" />
              <span>{finding}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
