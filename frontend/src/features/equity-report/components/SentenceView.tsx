import React from 'react';
import type { Sentence } from '../model/types';
import { useEquityReport } from './useEquityReport';
import { formatDisplayText, humanizeLocator } from '@/shared/lib/formatting';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';

export interface SentenceViewProps {
  sentence: Sentence;
  className?: string;
  hideCitations?: boolean;
  onOpenSource?: (noteNo: number) => void;
}

export const SentenceView: React.FC<SentenceViewProps> = ({
  sentence,
  className = '',
  hideCitations = false,
  onOpenSource: propOnOpenSource
}) => {
  const { getNoteNumbersForFactIds, sourceNotes, onOpenSource: ctxOnOpenSource } = useEquityReport();
  const onOpenSource = propOnOpenSource || ctxOnOpenSource;
  const noteNumbers = hideCitations ? [] : getNoteNumbersForFactIds(sentence.fact_ids || []);

  const visibleNotes = noteNumbers.slice(0, 3);
  const hiddenNotes = noteNumbers.slice(3);

  const hiddenLabel =
    hiddenNotes.length > 0
      ? `Và ${hiddenNotes.length} nguồn khác: ${hiddenNotes.join(', ')}`
      : undefined;

  return (
    <span className={className}>
      {formatDisplayText(sentence.text)}
      {!hideCitations && noteNumbers.length > 0 && (
        <TooltipProvider delayDuration={200}>
          <sup className="text-[11px] font-mono select-none">
          {visibleNotes.map((no, idx) => {
            const note = sourceNotes?.find((n) => n.note_no === no);
            const loc = note?.locator ? humanizeLocator(note.locator) : '';
            const tooltipText = note
              ? `${formatDisplayText(note.title)}${loc ? ` · ${formatDisplayText(loc)}` : ''}`
              : `Nguồn #${no}`;

            return (
              <React.Fragment key={no}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <a
                      href={`#note-${no}`}
                      onClick={(e) => {
                        if (onOpenSource) {
                          e.preventDefault();
                          onOpenSource(no);
                        }
                      }}
                      title={tooltipText}
                      aria-label={tooltipText}
                      className="text-text-accent hover:underline px-0.5 font-medium cursor-pointer inline-block"
                    >
                      {no}
                    </a>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs font-sans leading-relaxed">
                    {tooltipText}
                  </TooltipContent>
                </Tooltip>
                {idx < visibleNotes.length - 1 && ','}
              </React.Fragment>
            );
          })}
          {hiddenNotes.length > 0 && (
            <>
              {' '}
              <Tooltip>
                <TooltipTrigger asChild>
                  <a
                    href="#source-notes"
                    title={hiddenLabel}
                    aria-label={hiddenLabel}
                    className="text-text-accent hover:underline px-0.5 font-medium cursor-pointer inline-block"
                  >
                    +{hiddenNotes.length}
                  </a>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs text-xs font-sans">
                  {hiddenLabel}
                </TooltipContent>
              </Tooltip>
            </>
          )}
        </sup>
        </TooltipProvider>
      )}
    </span>
  );
};
