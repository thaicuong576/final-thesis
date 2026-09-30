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
    <div className="mt-5 mb-2 font-sans">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-[44px] font-bold text-text-primary leading-none tracking-[-0.02em] font-sans tabular-nums">
          {displayVal}
        </span>
        {subLabel && (
          <span className="text-sm text-text-secondary font-medium">
            {subLabel}
          </span>
        )}
      </div>

      {block.sentences && block.sentences.length > 0 && (
        <div className="space-y-1.5 text-[15px] leading-relaxed text-text-primary mt-3">
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
