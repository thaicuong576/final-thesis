import React from 'react';
import type { SectionBlock } from '../model/types';
import { SentenceView } from './SentenceView';

export const Section: React.FC<{ block: SectionBlock; compact?: boolean; className?: string }> = ({
  block,
  compact = false,
  className = ''
}) => {
  return (
    <section className={`font-sans max-w-[70ch] ${compact ? 'mt-4' : 'mt-7 mb-4'} ${className}`}>
      {block.title && (
        <h2
          className={
            compact
              ? 'text-[13px] font-semibold text-text-secondary leading-snug mb-1'
              : 'text-[18px] font-bold text-text-primary leading-snug mb-2'
          }
        >
          {block.title}
        </h2>
      )}
      {block.sentences && block.sentences.length > 0 && (
        <div className={compact ? 'space-y-1 text-[15px] leading-relaxed text-text-primary' : 'space-y-2 text-[15px] leading-[1.7] text-text-primary'}>
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
