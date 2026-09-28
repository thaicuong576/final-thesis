import { createContext, useContext } from 'react';
import type { AdaptiveReportResponse, SourceNote, Fact, Dataset, MetricPresentation } from '../model/types';

export interface EquityReportContextValue {
  report: AdaptiveReportResponse;
  sourceNotes: SourceNote[];
  facts: Fact[];
  datasets: Dataset[];
  metrics: MetricPresentation[];
  highlight: string[];
  getNoteNumbersForFactIds: (factIds: string[]) => number[];
}

export const EquityReportContext = createContext<EquityReportContextValue | null>(null);

export const useEquityReport = (): EquityReportContextValue => {
  const ctx = useContext(EquityReportContext);
  if (!ctx) {
    throw new Error('useEquityReport must be used within an EquityReportProvider');
  }
  return ctx;
};
