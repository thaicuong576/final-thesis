import React from 'react';
import { useEquityReport } from './useEquityReport';

export const ProcessLink: React.FC<{ onClick?: () => void }> = ({ onClick }) => {
  const { report } = useEquityReport();

  const revSummary = report.revision_summary as {
    rounds_executed?: number;
    agent_count?: number;
    duration_seconds?: number;
  } | null;

  const agents = revSummary?.agent_count || 3;
  const rounds = revSummary?.rounds_executed || 2;
  const duration = revSummary?.duration_seconds || 38;

  const label = `Xem quá trình phân tích · ${agents} agent · ${rounds} vòng phản biện · ${duration} giây`;

  return (
    <div className="my-4 text-sm print:hidden">
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-1.5 text-text-accent hover:underline font-medium p-0 bg-transparent border-none cursor-pointer"
      >
        <span>↳</span>
        <span>{label}</span>
      </button>
    </div>
  );
};
