import React, { useMemo } from 'react';
import type { AdaptiveReportResponse, MetricPresentation } from '../model/types';
import { EquityReportContext } from './useEquityReport';

export const EquityReportProvider: React.FC<{
  report: AdaptiveReportResponse;
  metrics?: MetricPresentation[];
  onOpenSource?: (noteNo: number) => void;
  onOpenFact?: (factId: string) => void;
  children: React.ReactNode;
}> = ({ report, metrics = [], onOpenSource, onOpenFact, children }) => {
  const sourceNotes = useMemo(() => report.source_notes || [], [report.source_notes]);
  const facts = useMemo(() => report.facts || [], [report.facts]);
  const datasets = useMemo(() => report.datasets || [], [report.datasets]);

  // Derive highlight entities
  const highlight = useMemo(() => {
    const fromDatasets = datasets.flatMap((d) => d.highlight_entity_ids || []);
    if (fromDatasets.length > 0) return Array.from(new Set(fromDatasets));
    const targetTicker = (report as { target_ticker?: string }).target_ticker;
    if (targetTicker) return [targetTicker];
    return [];
  }, [datasets, report]);

  const getNoteNumbersForFactIds = useMemo(() => {
    return (factIds: string[]): number[] => {
      if (!factIds || factIds.length === 0 || sourceNotes.length === 0) return [];
      const set = new Set<number>();
      for (const fId of factIds) {
        for (const note of sourceNotes) {
          if (note.fact_ids && note.fact_ids.includes(fId)) {
            set.add(note.note_no);
          }
        }
      }
      return Array.from(set).sort((a, b) => a - b);
    };
  }, [sourceNotes]);

  const value = useMemo(
    () => ({
      report,
      sourceNotes,
      facts,
      datasets,
      metrics,
      highlight,
      getNoteNumbersForFactIds,
      onOpenSource,
      onOpenFact
    }),
    [report, sourceNotes, facts, datasets, metrics, highlight, getNoteNumbersForFactIds, onOpenSource, onOpenFact]
  );

  return <EquityReportContext.Provider value={value}>{children}</EquityReportContext.Provider>;
};
