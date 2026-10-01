import type { AnalysisCapabilities } from '../model/types';
import { getApiBaseUrl } from '@/shared/lib/apiUrl';

export interface CapabilityService {
  getCapabilities(): Promise<AnalysisCapabilities>;
}

export const capabilityService: CapabilityService = {
  async getCapabilities(): Promise<AnalysisCapabilities> {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/api/capabilities`, {
      headers: { Accept: 'application/json' }
    });
    if (!response.ok) {
      throw new Error(`Không thể tải phạm vi dữ liệu (HTTP ${response.status}).`);
    }
    const raw = (await response.json()) as Partial<AnalysisCapabilities> & {
      datasetSnapshotId?: string | null;
      peerUniverses?: AnalysisCapabilities['peerUniverses'];
    };
    if (
      !Array.isArray(raw?.entities) ||
      !Array.isArray(raw.periods) ||
      !Array.isArray(raw.metrics) ||
      (raw.macro !== undefined && raw.macro !== null && typeof raw.macro !== 'object') ||
      (raw.implemented_capabilities !== undefined && !Array.isArray(raw.implemented_capabilities)) ||
      (raw.supported_operations !== undefined && !Array.isArray(raw.supported_operations)) ||
      (raw.analysis_available !== undefined && typeof raw.analysis_available !== 'boolean') ||
      (raw.datasetSnapshotId !== undefined && raw.datasetSnapshotId !== null && typeof raw.datasetSnapshotId !== 'string') ||
      (raw.dataset_snapshot_id !== undefined && raw.dataset_snapshot_id !== null && typeof raw.dataset_snapshot_id !== 'string')
    ) {
      throw new Error('API trả về phạm vi dữ liệu không hợp lệ.');
    }
    const peerUniverses = raw.peerUniverses ?? [];
    return {
      ...raw,
      entities: raw.entities as AnalysisCapabilities['entities'],
      periods: raw.periods as AnalysisCapabilities['periods'],
      metrics: raw.metrics as AnalysisCapabilities['metrics'],
      macro: (raw.macro ?? {
        status: 'UNAVAILABLE',
        minimumContractSatisfied: false,
        summary: 'Chưa có thông tin vĩ mô',
        details: 'API chưa công bố năng lực dữ liệu vĩ mô.'
      }) as AnalysisCapabilities['macro'],
      snapshotId: raw.snapshotId ?? null,
      datasetId: raw.datasetId ?? null,
      datasetSnapshotId: raw.datasetSnapshotId ?? raw.dataset_snapshot_id ?? null,
      dataset_snapshot_id: raw.dataset_snapshot_id ?? raw.datasetSnapshotId ?? null,
      analysis_available: raw.analysis_available === true,
      implemented_capabilities: raw.implemented_capabilities ?? [],
      supported_operations: raw.supported_operations ?? [],
      topics: raw.topics ?? [],
      peerUniverses,
      peerUniverse: raw.peerUniverse ?? peerUniverses[0] ?? null,
      ingestionTimestamp: raw.ingestionTimestamp ?? null,
      validationTimestamp: raw.validationTimestamp ?? null,
      source: raw.source ?? null,
      readiness: raw.readiness ?? null,
      coverage: Array.isArray(raw.coverage) ? (raw.coverage as AnalysisCapabilities['coverage']) : []
    };
  }
};
