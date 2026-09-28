import React from 'react';
import type { AnalysisReport } from '../model/types';
import { AnalysisReportWorkspace } from './AnalysisReportWorkspace';

export interface LegacyReportProps {
  report: AnalysisReport;
  isDemo?: boolean;
}

export const LegacyReport: React.FC<LegacyReportProps> = ({ report, isDemo = false }) => {
  return <AnalysisReportWorkspace report={report} isDemo={isDemo} />;
};
