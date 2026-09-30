import React from 'react';
import { useEquityReport } from './useEquityReport';
import { ReportMasthead } from './ReportMasthead';
import { BlockRenderer } from './BlockRenderer';
import { SignalsAside } from './SignalsAside';
import { ProcessLink } from './ProcessLink';
import { SourceNotes } from './SourceNotes';
import { TechnicalDetails } from './TechnicalDetails';
import { normalizeBlocks } from '../model/normalizeBlocks';
import { KpiBand } from './KpiBand';

export const NoteLayout: React.FC = () => {
  const { report, datasets } = useEquityReport();
  const blocks = normalizeBlocks(report.report_spec?.blocks || [], report.report_spec?.kind, datasets);
  const signals = report.signals || [];
  const isProfile = report.question_type === 'company_profile' && signals.length > 0;

  // Company profile: the headline spans the page, then the opening prose (everything before the
  // first figure or table) sits beside the peer-signal panel. Figures below get the full width,
  // so wide charts such as the rank heatmap are never squeezed next to the panel.
  const showKpis = report.question_type === 'company_profile' || report.question_type === 'trend';
  const headline = (isProfile || showKpis) && blocks[0]?.type === 'headline' ? blocks[0] : null;
  const body = headline ? blocks.slice(1) : blocks;
  const firstVisual = body.findIndex((b) => b.type === 'figure' || b.type === 'table');
  const lead = isProfile ? (firstVisual === -1 ? body : body.slice(0, firstVisual)) : [];
  const rest = isProfile ? (firstVisual === -1 ? [] : body.slice(firstVisual)) : body;

  return (
    <article className="report-sheet mx-auto w-full max-w-[920px] overflow-hidden rounded-2xl border border-border-subtle bg-surface-primary px-5 py-6 font-sans shadow-[0_1px_2px_rgba(29,28,26,0.04),0_24px_50px_-30px_rgba(60,45,20,0.4)] sm:px-10 sm:py-9">
      <ReportMasthead />

      {headline && <BlockRenderer block={headline} />}
      {showKpis && <KpiBand />}

      {isProfile && (
        <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_280px] gap-x-8 gap-y-5 items-start mt-2">
          <div className="min-w-0">
            {lead.map((block, idx) => (
              <BlockRenderer key={idx} block={block} />
            ))}
          </div>
          <SignalsAside signals={signals} />
        </div>
      )}

      <div className="min-w-0">
        {rest.map((block, idx) => (
          <BlockRenderer key={idx} block={block} />
        ))}
      </div>

      <ProcessLink />
      <SourceNotes />
      <TechnicalDetails />
    </article>
  );
};
