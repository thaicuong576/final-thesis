import React from 'react';
import { useEquityReport } from './useEquityReport';
import { ReportMasthead } from './ReportMasthead';
import { BlockRenderer } from './BlockRenderer';
import { ProcessLink } from './ProcessLink';
import { SourceNotes } from './SourceNotes';
import { TechnicalDetails } from './TechnicalDetails';
import { normalizeBlocks } from '../model/normalizeBlocks';

export const AnswerCardLayout: React.FC = () => {
  const { report, datasets } = useEquityReport();
  const blocks = normalizeBlocks(report.report_spec?.blocks || [], report.report_spec?.kind, datasets);
  const query = (report as { query?: string }).query;

  return (
    <article className="report-sheet w-full max-w-[720px] mx-auto px-5 py-6 sm:px-9 sm:py-8 bg-surface-primary border border-border-subtle rounded-xl font-sans shadow-[0_1px_2px_rgba(32,32,30,0.04),0_8px_24px_-12px_rgba(32,32,30,0.12)]">
      <ReportMasthead />

      {query && <p className="text-sm text-text-secondary mt-1 mb-0">&ldquo;{query}&rdquo;</p>}

      <div>
        {blocks.map((block, idx) => (
          <BlockRenderer key={idx} block={block} compact />
        ))}
      </div>

      <ProcessLink />
      <SourceNotes />
      <TechnicalDetails />
    </article>
  );
};
