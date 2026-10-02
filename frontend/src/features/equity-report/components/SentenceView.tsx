import React from 'react';
import type { Sentence } from '../model/types';
import { useEquityReport } from './useEquityReport';
import { formatDisplayText } from '@/shared/lib/formatting';

export interface SentenceViewProps {
  sentence: Sentence;
  className?: string;
  hideCitations?: boolean;
}

export const SentenceView: React.FC<SentenceViewProps> = ({
  sentence,
  className = '',
  hideCitations = false
}) => {
  const { getNoteNumbersForFactIds } = useEquityReport();
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
        <sup>
          {visibleNotes.map((no, idx) => (
            <React.Fragment key={no}>
              <a
                href={`#note-${no}`}
                className="text-text-accent hover:underline px-0.5 font-medium"
              >
                {no}
              </a>
              {idx < visibleNotes.length - 1 && ','}
            </React.Fragment>
          ))}
          {hiddenNotes.length > 0 && (
            <>
              {' '}
              <a
                href="#source-notes"
                title={hiddenLabel}
                aria-label={hiddenLabel}
                className="text-text-accent hover:underline px-0.5 font-medium"
              >
                +{hiddenNotes.length}
              </a>
            </>
          )}
        </sup>
      )}
    </span>
  );
};
