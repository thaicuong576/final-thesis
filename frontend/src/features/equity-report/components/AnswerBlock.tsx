import React from 'react';
import type { AnswerBlock as AnswerBlockType } from '../model/types';
import { useEquityReport } from './useEquityReport';
import { getMetricPresentation, formatMetricValue } from '../model/metricRegistry';
import { fmtPeriod } from '@/shared/lib/formatting';
import { SentenceView } from './SentenceView';

export const AnswerBlock: React.FC<{ block: AnswerBlockType }> = ({ block }) => {
  const { facts, metrics } = useEquityReport();

  // Find fact by value_fact_id
  const targetFact = facts.find((f) => f.fact_id === block.value_fact_id);
  const metricId = targetFact?.metric_id || '';
  const metricMeta = getMetricPresentation(metricId, metrics);

  const displayVal = targetFact
    ? formatMetricValue(targetFact.value, metricMeta)
    : '—';

  const entity = targetFact?.entity_id || '';
  const periodStr = fmtPeriod(targetFact?.period);

  const labelParts = [metricMeta.shortLabel, entity, periodStr].filter(Boolean);
  const subLabel = labelParts.join(' · ');

  return (
    <div className="my-4 font-sans">
      <div className="flex items-baseline gap-3 my-2">
        <span className="text-[32px] font-bold text-text-primary leading-tight font-mono">
          {displayVal}
        </span>
        {subLabel && (
          <span className="text-xs text-text-muted font-medium">
            {subLabel}
          </span>
        )}
      </div>

      {block.sentences && block.sentences.length > 0 && (
        <div className="space-y-1.5 text-sm leading-relaxed text-text-primary mt-2">
          {block.sentences.map((sentence) => (
            <p key={sentence.sentence_id} className="m-0">
              <SentenceView sentence={sentence} />
            </p>
          ))}
        </div>
      )}
    </div>
  );
};
