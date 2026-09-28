import React from 'react';
import type { CalloutBlock } from '../model/types';
import { SentenceView } from './SentenceView';

export const Callout: React.FC<{ block: CalloutBlock }> = ({ block }) => {
  const isWarning = block.tone === 'warning';

  return (
    <div
      className={`my-4 pl-3 py-1 text-sm font-sans ${
        isWarning
          ? 'border-l-2 border-warning'
          : 'border-l-2 border-border-strong'
      }`}
    >
      {block.title && (
        <div className="text-xs font-semibold text-text-primary mb-1">
          {block.title}
        </div>
      )}
      {block.sentences && block.sentences.length > 0 && (
        <div className="space-y-1 text-sm leading-[1.6] text-text-primary">
          {block.sentences.map((sentence, idx) => (
            <p key={sentence.sentence_id || idx} className="m-0">
              <SentenceView sentence={sentence} />
            </p>
          ))}
        </div>
      )}
    </div>
  );
};
