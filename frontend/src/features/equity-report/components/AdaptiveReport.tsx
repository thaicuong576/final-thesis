import React from 'react';
import type { AdaptiveReportResponse, MetricPresentation } from '../model/types';
import { EquityReportProvider } from './EquityReportContext';
import { AnswerCardLayout } from './AnswerCardLayout';
import { NoteLayout } from './NoteLayout';

export interface AdaptiveReportProps {
  report: AdaptiveReportResponse;
  metrics?: MetricPresentation[];
  className?: string;
}

export const AdaptiveReport: React.FC<AdaptiveReportProps> = ({ report, metrics, className = '' }) => {
  const isAnswerCard = report.report_spec?.kind === 'answer_card';

  return (
    <EquityReportProvider report={report} metrics={metrics}>
      <div className={`w-full max-w-full overflow-x-hidden py-4 sm:py-6 px-3 sm:px-6 lg:px-8 bg-workspace text-text-primary ${className}`}>
        {isAnswerCard ? <AnswerCardLayout /> : <NoteLayout />}
      </div>
    </EquityReportProvider>
  );
};
