import type { MacroCapabilityStatus } from '../../capability/model/types';

export interface AnalysisRequest {
  objective: string;
  analysisTargetIds: string[];
  periodIds: string[];
  metricIds: string[];
  peerUniverseId: string;
  macroStatus: MacroCapabilityStatus;
}

export interface AnalysisSubmissionReceipt {
  accepted: boolean;
  requestId: string;
  message: string;
}
