import React, { useMemo } from 'react';
import { useEquityReport } from './useEquityReport';
import { ReportMasthead } from './ReportMasthead';
import { BlockRenderer, type RenderableBlock } from './BlockRenderer';
import { SignalsAside } from './SignalsAside';
import { ProcessLink } from './ProcessLink';
import { SourceNotes } from './SourceNotes';
import { TechnicalDetails } from './TechnicalDetails';
import { normalizeBlocks, type NormalizedBlock } from '../model/normalizeBlocks';
import { KpiBand } from './KpiBand';

function groupBlocksWithFigures(items: NormalizedBlock[]): RenderableBlock[] {
  const result: RenderableBlock[] = [];
  let i = 0;
  while (i < items.length) {
    const curr = items[i];
    const next = items[i + 1];
    if (curr.type === 'section' && next && next.type === 'figure') {
      result.push({
        type: 'section_figure',
        section: curr,
        figure: next
      });
      i += 2;
    } else {
      result.push(curr);
      i += 1;
    }
  }
  return result;
}

export const NoteLayout: React.FC = () => {
  const { report, datasets } = useEquityReport();
  const rawBlocks = normalizeBlocks(report.report_spec?.blocks || [], report.report_spec?.kind, datasets);
  const signals = report.signals || [];
  const isProfile = report.question_type === 'company_profile' && signals.length > 0;

  const headline = rawBlocks[0]?.type === 'headline' ? rawBlocks[0] : null;
  const rawBody = headline ? rawBlocks.slice(1) : rawBlocks;

  const groupedBody = useMemo(() => groupBlocksWithFigures(rawBody), [rawBody]);

  // Visual or unit boundaries
  const firstVisual = groupedBody.findIndex(
    (b) => b.type === 'figure' || b.type === 'table' || b.type === 'section_figure'
  );
  const lead = isProfile ? (firstVisual === -1 ? groupedBody : groupedBody.slice(0, firstVisual)) : [];
  const rest = isProfile ? (firstVisual === -1 ? [] : groupedBody.slice(firstVisual)) : groupedBody;

  return (
    <article className="report-sheet mx-auto w-full max-w-[1040px] overflow-hidden rounded-2xl border border-border-subtle bg-surface-primary px-5 py-6 font-sans shadow-[0_1px_2px_rgba(29,28,26,0.04),0_24px_50px_-30px_rgba(60,45,20,0.4)] sm:px-10 sm:py-9">
      <ReportMasthead />

      {headline && <BlockRenderer block={headline} />}
      <KpiBand />

      {isProfile && lead.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_280px] gap-x-8 gap-y-5 items-start mt-2">
          <div className="min-w-0">
            {lead.map((block, idx) => (
              <BlockRenderer key={idx} block={block} />
            ))}
          </div>
          <SignalsAside signals={signals} />
        </div>
      )}

      {isProfile && lead.length === 0 && signals.length > 0 && (
        <div className="my-5">
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
