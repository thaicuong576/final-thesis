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
    <article className="report-sheet mx-auto w-full max-w-[760px] overflow-hidden rounded-2xl border border-border-subtle bg-surface-primary px-5 py-6 font-sans shadow-[0_1px_2px_rgba(29,28,26,0.04),0_24px_50px_-30px_rgba(60,45,20,0.4)] sm:px-10 sm:py-9">
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
