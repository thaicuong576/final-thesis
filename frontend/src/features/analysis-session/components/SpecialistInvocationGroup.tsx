import type { SpecialistInvocation } from '../model/types';
import { SpecialistInvocationCard } from './SpecialistInvocationCard';

interface SpecialistInvocationGroupProps {
  invocations: SpecialistInvocation[];
  onSelectInvocation: (invocation: SpecialistInvocation) => void;
}

export function SpecialistInvocationGroup({
  invocations,
  onSelectInvocation
}: SpecialistInvocationGroupProps) {
  if (invocations.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-wider text-muted">
            Chuyên môn đang thực hiện
          </h2>
          <p className="text-xs text-muted mt-0.5">
            Điều phối đã phân công {invocations.length} nhiệm vụ chuyên môn theo câu hỏi phân tích.
          </p>
        </div>
        <span className="text-xs font-semibold text-ink">
          {invocations.length} chuyên môn
        </span>
      </div>

      <div
        className={`grid gap-3.5 ${
          invocations.length === 1
            ? 'grid-cols-1'
            : invocations.length === 2
            ? 'grid-cols-1 md:grid-cols-2'
            : 'grid-cols-1 md:grid-cols-3'
        }`}
      >
        {invocations.map((invocation) => (
          <SpecialistInvocationCard
            key={invocation.id}
            invocation={invocation}
            onClick={() => onSelectInvocation(invocation)}
          />
        ))}
      </div>
    </div>
  );
}
