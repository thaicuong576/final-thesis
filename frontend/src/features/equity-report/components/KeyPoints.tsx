import React from 'react';
import type { KeyPointsBlock } from '../model/types';
import { SentenceView } from './SentenceView';
import { formatDisplayText } from '@/shared/lib/formatting';

export const KeyPoints: React.FC<{ block: KeyPointsBlock }> = ({ block }) => {
  const items = block.items || [];

  return (
    <div className="space-y-3 my-3 text-[15px] leading-[1.65] text-text-primary font-sans">
      {items.map((item, idx) => (
        <p key={idx} className="m-0">
          {item.title && (
            <span className="font-semibold text-text-primary mr-1">
              {formatDisplayText(item.title.endsWith('.') ? item.title : `${item.title}.`)}
            </span>
          )}
          {item.sentences?.map((sentence, sIdx) => (
            <span key={sentence.sentence_id || sIdx} className="inline mr-1">
              <SentenceView sentence={sentence} />
            </span>
          ))}
        </p>
      ))}
    </div>
  );
};
