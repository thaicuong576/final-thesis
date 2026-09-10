export interface AnalysisRequest {
  objective: string;
  analysisTargetIds: string[];
  periodIds: string[];
  metricIds: string[];
  capabilitySnapshotId: string;
  peerUniverseId: string;
}

export type AnalysisSubmissionStatus = 'CLIENT_VALIDATED';

export interface AnalysisSubmissionReceipt {
  status: AnalysisSubmissionStatus;
  readyForBackendSubmission: boolean;
  requestId: string;
  message: string;
}
