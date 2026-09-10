import { getMockCapabilities } from './mockCapabilityProvider';
import type { AnalysisCapabilities } from '../model/types';

export interface CapabilityService {
  getCapabilities(): Promise<AnalysisCapabilities>;
}

// Replace this implementation with GET /api/capabilities without changing UI components.
export const capabilityService: CapabilityService = {
  getCapabilities: getMockCapabilities
};
