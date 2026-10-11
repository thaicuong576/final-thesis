import React from 'react';
import type { NormalizedBlock, NormalizedFigureBlock } from '../model/normalizeBlocks';
import type { SectionBlock } from '../model/types';
import { useEquityReport } from './useEquityReport';
import { AnswerBlock } from './AnswerBlock';
import { Headline } from './Headline';
import { KeyPoints } from './KeyPoints';
import { Section } from './Section';
import { Figure } from './Figure';
import { Callout } from './Callout';
import { SectionFigureUnit } from './SectionFigureUnit';
import { DataTable } from '../charts';

export type SectionFigureBlock = {
  type: 'section_figure';
  section: SectionBlock;
  figure: NormalizedFigureBlock;
};

export type RenderableBlock = NormalizedBlock | SectionFigureBlock;

export const BlockRenderer: React.FC<{ block: RenderableBlock; compact?: boolean }> = ({ block, compact = false }) => {
  const { datasets, metrics, highlight } = useEquityReport();

  switch (block.type) {
    case 'answer':
      return <AnswerBlock block={block} />;

    case 'headline':
      return <Headline block={block} />;

    case 'key_points':
      return <KeyPoints block={block} />;

    case 'section':
      return <Section block={block} compact={compact} />;

    case 'figure':
      return <Figure block={block} />;

    case 'section_figure':
      return <SectionFigureUnit section={block.section} figure={block.figure} compact={compact} />;

    case 'callout':
      return <Callout block={block} />;

    case 'table': {
      const dataset = datasets.find((d) => d.dataset_id === block.dataset_id) || {
        dataset_id: block.dataset_id,
        shape: 'kpi',
        title: block.title,
        produced_by: { tool: 'unknown', agent: 'system' },
        metric_ids: [],
        periods: [],
        highlight_entity_ids: highlight,
        rows: [],
        reference_lines: [],
        allowed_charts: []
      };
      return (
        <div className="my-4">
          {block.title && (
            <h3 className="text-sm font-semibold text-text-primary mb-1">
              {block.title}
            </h3>
          )}
          <DataTable dataset={dataset} metrics={metrics} highlight={highlight} />
        </div>
      );
    }

    default:
      console.warn('Unknown block type:', (block as { type?: string }).type);
      return null;
  }
};
