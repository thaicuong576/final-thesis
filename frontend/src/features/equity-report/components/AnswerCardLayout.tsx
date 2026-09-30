import React from 'react';
import { useEquityReport } from './useEquityReport';
import { ReportMasthead } from './ReportMasthead';
import { BlockRenderer } from './BlockRenderer';
import { SourceNotes } from './SourceNotes';
import { TechnicalDetails } from './TechnicalDetails';

export const AnswerCardLayout: React.FC = () => {
  const { report } = useEquityReport();
  const blocks = report.report_spec?.blocks || [];
  const query = (report as { query?: string }).query;

  return (
    <article className="w-full max-w-[720px] mx-auto p-4 sm:p-7 bg-surface-primary border border-line rounded-lg font-sans shadow-sm overflow-hidden">
      <ReportMasthead />

      {query && (
        <div className="text-xs sm:text-sm text-text-secondary italic my-2">
          &ldquo;{query}&rdquo;
        </div>
      )}

      <div className="space-y-4 my-3">
        {blocks.map((block, idx) => (
          <BlockRenderer key={idx} block={block} />
        ))}
      </div>

      <SourceNotes />
      <TechnicalDetails />
    </article>
  );
};
