import React from 'react';
import type { HeadlineBlock } from '../model/types';
import { SentenceView } from './SentenceView';

export const Headline: React.FC<{ block: HeadlineBlock }> = ({ block }) => {
  return (
    <h1 className="text-[26px] md:text-[28px] font-bold text-text-primary leading-[1.25] tracking-[-0.015em] my-3">
      <SentenceView sentence={block.sentence} />
    </h1>
  );
};
