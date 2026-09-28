import React from 'react';
import type { ReportBlock } from '../model/types';
import { useEquityReport } from './useEquityReport';
import { AnswerBlock } from './AnswerBlock';
import { Headline } from './Headline';
import { KeyPoints } from './KeyPoints';
import { Section } from './Section';
import { Figure } from './Figure';
import { Callout } from './Callout';
import { DataTable } from '../charts';

export const BlockRenderer: React.FC<{ block: ReportBlock }> = ({ block }) => {
  const { datasets, metrics, highlight } = useEquityReport();

  switch (block.type) {
    case 'answer':
      return <AnswerBlock block={block} />;

    case 'headline':
      return <Headline block={block} />;

    case 'key_points':
      return <KeyPoints block={block} />;

    case 'section':
      return <Section block={block} />;

    case 'figure':
      return <Figure block={block} />;

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
