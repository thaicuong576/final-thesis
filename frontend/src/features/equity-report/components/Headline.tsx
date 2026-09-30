import React from 'react';
import type { HeadlineBlock } from '../model/types';
import { SentenceView } from './SentenceView';

export const Headline: React.FC<{ block: HeadlineBlock }> = ({ block }) => {
  return (
    <h1 className="font-display mt-1 mb-3 text-[28px] font-bold leading-[1.18] text-balance text-text-primary md:text-[34px]">
      <SentenceView sentence={block.sentence} />
    </h1>
  );
};
