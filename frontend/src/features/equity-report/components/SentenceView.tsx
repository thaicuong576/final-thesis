import React from 'react';
import type { Sentence } from '../model/types';
import { useEquityReport } from './useEquityReport';
import { formatDisplayText } from '@/shared/lib/formatting';

export interface SentenceViewProps {
  sentence: Sentence;
  className?: string;
}

export const SentenceView: React.FC<SentenceViewProps> = ({ sentence, className = '' }) => {
  const { getNoteNumbersForFactIds } = useEquityReport();
  const noteNumbers = getNoteNumbersForFactIds(sentence.fact_ids || []);

  return (
    <span className={className}>
      {formatDisplayText(sentence.text)}
      {noteNumbers.length > 0 && (
        <sup>
          {noteNumbers.map((no, idx) => (
            <React.Fragment key={no}>
              <a
                href={`#note-${no}`}
                className="text-text-accent hover:underline px-0.5 font-medium"
              >
                {no}
              </a>
              {idx < noteNumbers.length - 1 && ','}
            </React.Fragment>
          ))}
        </sup>
      )}
    </span>
  );
};
