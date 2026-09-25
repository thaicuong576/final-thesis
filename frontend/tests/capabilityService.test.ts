import { afterEach, describe, expect, it, vi } from 'vitest';
import { capabilityService } from '../src/entities/capability/api/capabilityService';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';
import { DEFAULT_RENDER_BACKEND, getApiBaseUrl } from '../src/shared/lib/apiUrl';
import { getResolvedApiEndpoint } from '../src/features/analysis-session/useAnalysisSessionStream';

describe('capabilityService API URL', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it('uses the stream backend resolver when VITE_API_BASE_URL is unset', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '');
    vi.stubGlobal('window', { location: { hostname: 'final-thesis.vercel.app' } });
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockCapabilities
    } as Response);

    await capabilityService.getCapabilities();

    expect(getApiBaseUrl()).toBe(DEFAULT_RENDER_BACKEND);
    expect(getResolvedApiEndpoint()).toBe(`${DEFAULT_RENDER_BACKEND}/api/analyze/stream`);
    expect(fetchSpy).toHaveBeenCalledWith(`${DEFAULT_RENDER_BACKEND}/api/capabilities`, {
      headers: { Accept: 'application/json' }
    });
  });
});
