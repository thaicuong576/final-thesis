import React from 'react';
import type { SectionBlock } from '../model/types';
import { SentenceView } from './SentenceView';

export const Section: React.FC<{ block: SectionBlock }> = ({ block }) => {
  return (
    <section className="my-4 font-sans">
      {block.title && (
        <h2 className="text-[18px] font-bold text-text-primary leading-snug mb-2">
          {block.title}
        </h2>
      )}
      {block.sentences && block.sentences.length > 0 && (
        <div className="space-y-2 text-[15px] leading-relaxed text-text-primary">
          {block.sentences.map((s, idx) => (
            <p key={s.sentence_id || idx} className="m-0">
              <SentenceView sentence={s} />
            </p>
          ))}
        </div>
      )}
    </section>
  );
};
