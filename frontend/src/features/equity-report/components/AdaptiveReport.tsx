import React, { useState, useCallback } from 'react';
import type { AdaptiveReportResponse, MetricPresentation } from '../model/types';
import { EquityReportProvider } from './EquityReportContext';
import { AnswerCardLayout } from './AnswerCardLayout';
import { NoteLayout } from './NoteLayout';
import { SourceDrawer } from '../../source-lineage/SourceDrawer';
import type { LineageTab } from '../../source-lineage/types';
import { FocalValuationCard, ValuationScatterChart } from '../../market-context';

import { TooltipProvider } from '@/components/ui/tooltip';

export interface AdaptiveReportProps {
  report: AdaptiveReportResponse;
  metrics?: MetricPresentation[];
  className?: string;
  onOpenSource?: (noteNo: number) => void;
}

export const AdaptiveReport: React.FC<AdaptiveReportProps> = ({
  report,
  metrics,
  className = '',
  onOpenSource
}) => {
  const isAnswerCard = report.report_spec?.kind === 'answer_card';

  const [drawerState, setDrawerState] = useState<{
    isOpen: boolean;
    noteNo?: number;
    factId?: string;
    observationId?: string;
    defaultTab?: LineageTab;
  }>({ isOpen: false });

  const handleOpenSource = useCallback(
    (noteNo: number) => {
      setDrawerState({
        isOpen: true,
        noteNo,
        defaultTab: 'document',
      });
      onOpenSource?.(noteNo);
    },
    [onOpenSource]
  );

  const handleOpenFact = useCallback((factId: string) => {
    setDrawerState({
      isOpen: true,
      factId,
      defaultTab: 'data',
    });
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setDrawerState((prev) => ({ ...prev, isOpen: false }));
  }, []);

  const focalTicker: string | null =
    (typeof report.target_ticker === 'string' ? report.target_ticker : null) ||
    report.facts?.find((f) => Boolean(f.entity_id))?.entity_id ||
    null;

  return (
    <TooltipProvider delayDuration={200}>
      <EquityReportProvider
        report={report}
        metrics={metrics}
        onOpenSource={handleOpenSource}
        onOpenFact={handleOpenFact}
      >
        <div className={`w-full max-w-full overflow-x-hidden py-4 sm:py-6 px-3 sm:px-6 lg:px-8 text-text-primary ${className}`}>
          {focalTicker && (
            <div className="max-w-4xl mx-auto mb-4">
              <FocalValuationCard ticker={focalTicker} />
            </div>
          )}
          {isAnswerCard ? <AnswerCardLayout /> : <NoteLayout />}
          <div className="max-w-4xl mx-auto mt-6">
            <ValuationScatterChart focalTicker={focalTicker} />
          </div>
        </div>
        <SourceDrawer
          isOpen={drawerState.isOpen}
          onClose={handleCloseDrawer}
          noteNo={drawerState.noteNo}
          factId={drawerState.factId}
          observationId={drawerState.observationId}
          report={report}
          defaultTab={drawerState.defaultTab}
        />
      </EquityReportProvider>
    </TooltipProvider>
  );
};

