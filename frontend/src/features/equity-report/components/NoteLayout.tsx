import React from 'react';
import { useEquityReport } from './useEquityReport';
import { ReportMasthead } from './ReportMasthead';
import { BlockRenderer } from './BlockRenderer';
import { SignalsAside } from './SignalsAside';
import { ProcessLink } from './ProcessLink';
import { SourceNotes } from './SourceNotes';
import { TechnicalDetails } from './TechnicalDetails';

export const NoteLayout: React.FC = () => {
  const { report } = useEquityReport();
  const blocks = report.report_spec?.blocks || [];
  const signals = report.signals || [];
  const isProfile = report.question_type === 'company_profile' && signals.length > 0;

  // For company profile with signals:
  // Headline is rendered first, then KeyPoints is paired with SignalsAside in a 1.6fr / 1fr grid.
  // If no headline, the first block is paired with SignalsAside.
  let headerBlock = null;
  let contentBlocks = blocks;

  if (isProfile && blocks.length > 0) {
    if (blocks[0].type === 'headline') {
      headerBlock = blocks[0];
      contentBlocks = blocks.slice(1);
    }
  }

  return (
    <article className="w-full max-w-[860px] mx-auto p-4 sm:p-8 bg-surface-primary border border-line rounded-lg font-sans shadow-sm overflow-hidden">
      <ReportMasthead />

      {isProfile ? (
        <div className="space-y-5">
          {headerBlock && <BlockRenderer block={headerBlock} />}

          <div>
            <div className="md:float-right md:w-[280px] md:ml-6 md:mb-4 mb-5">
              <SignalsAside signals={signals} />
            </div>

            <div className="space-y-4">
              {contentBlocks.map((block, idx) => (
                <div key={idx}>
                  <BlockRenderer block={block} />
                </div>
              ))}
            </div>
            <div className="clear-both" />
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {blocks.map((block, idx) => (
            <div key={idx}>
              <BlockRenderer block={block} />
            </div>
          ))}
        </div>
      )}

      <ProcessLink />
      <SourceNotes />
      <TechnicalDetails />
    </article>
  );
};
