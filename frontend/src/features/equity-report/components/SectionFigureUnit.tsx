import React from 'react';
import type { SectionBlock } from '../model/types';
import type { NormalizedFigureBlock } from '../model/normalizeBlocks';
import { Section } from './Section';
import { Figure } from './Figure';

export interface SectionFigureUnitProps {
  section: SectionBlock;
  figure: NormalizedFigureBlock;
  compact?: boolean;
}

/**
 * Renders a section and its associated figure as one unified editorial unit:
 * on desktop (>= 1024px), the section text and chart sit side-by-side in two columns;
 * on narrow screens, they stack naturally.
 */
export const SectionFigureUnit: React.FC<SectionFigureUnitProps> = ({
  section,
  figure,
  compact = false
}) => {
  return (
    <div
      data-testid="section-figure-unit"
      className="my-6 grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8 items-start break-inside-avoid"
    >
      <div className="min-w-0 max-w-[70ch]">
        <Section block={section} compact={compact} className="mt-0 mb-0" />
      </div>
      <div className="min-w-0">
        <Figure block={figure} />
      </div>
    </div>
  );
};
