import { getMockCapabilities } from './mockCapabilityProvider';
import type { AnalysisCapabilities } from '../model/types';

export interface CapabilityService {
  getCapabilities(): Promise<AnalysisCapabilities>;
}

export const capabilityService: CapabilityService = {
  async getCapabilities(): Promise<AnalysisCapabilities> {
    try {
      const baseUrl =
        typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL
          ? import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')
          : '';
      const endpoint = `${baseUrl}/api/capabilities`;
      const response = await fetch(endpoint, {
        headers: { Accept: 'application/json' }
      });
      if (response.ok) {
        const data = (await response.json()) as AnalysisCapabilities;
        if (data && Array.isArray(data.entities) && data.entities.length > 0) {
          return data;
        }
      }
    } catch {
      // Fallback in offline or unit test environments
    }
    return getMockCapabilities();
  }
};
