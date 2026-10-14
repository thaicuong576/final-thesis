import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  apiFetch,
  fetchAuthStatus,
  performLogin,
  AUTH_EXPIRED_EVENT,
  type AuthExpiredDetail,
} from '../src/shared/api/apiClient';
import { saveSession, getSession, clearSession } from '../src/features/auth/model/authStorage';

describe('apiClient', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('attaches Authorization header to /api/* requests when token exists', async () => {
    saveSession({
      access_token: 'test-token-abc',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
    });

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    await apiFetch('/api/capabilities');

    expect(fetchSpy).toHaveBeenCalled();
    const calledInit = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = new Headers(calledInit.headers);
    expect(headers.get('Authorization')).toBe('Bearer test-token-abc');
  });

  it('does not attach Authorization header if no token is stored', async () => {
    clearSession();
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    await apiFetch('/api/version');

    const calledInit = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = new Headers(calledInit.headers);
    expect(headers.has('Authorization')).toBe(false);
  });

  it('clears session and dispatches AUTH_EXPIRED_EVENT when receiving 401 on /api/*', async () => {
    saveSession({
      access_token: 'expiring-token',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Token expired', code: 'auth_required' }), {
        status: 401,
      })
    );

    let expiredEventDetail: AuthExpiredDetail | null = null;
    const listener = (event: Event) => {
      expiredEventDetail = (event as CustomEvent<AuthExpiredDetail>).detail;
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, listener);

    const response = await apiFetch('/api/capabilities');

    expect(response.status).toBe(401);
    expect(getSession()).toBeNull();
    expect(expiredEventDetail).not.toBeNull();
    expect((expiredEventDetail as unknown as AuthExpiredDetail).message).toContain('Phiên đã hết hạn');

    window.removeEventListener(AUTH_EXPIRED_EVENT, listener);
  });

  it('does not dispatch AUTH_EXPIRED_EVENT on 401 from /api/auth/login', async () => {
    saveSession({
      access_token: 'valid-token',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Invalid credentials', code: 'invalid_credentials' }), {
        status: 401,
      })
    );

    let eventFired = false;
    const listener = () => {
      eventFired = true;
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, listener);

    try {
      await performLogin({ username: 'bad', password: 'wrong' });
    } catch {
      // Expected error
    }

    expect(eventFired).toBe(false);
    window.removeEventListener(AUTH_EXPIRED_EVENT, listener);
  });

  it('fetchAuthStatus retrieves { required: boolean }', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ required: true }), { status: 200 })
    );

    const status = await fetchAuthStatus();
    expect(status.required).toBe(true);
  });

  it('performLogin handles successful response and 429 rate limit response', async () => {
    // Test 200 OK
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token: 'new-token',
          token_type: 'bearer',
          expires_at: '2026-10-15T00:00:00Z',
        }),
        { status: 200 }
      )
    );

    const result = await performLogin({ username: 'user', password: 'pass' });
    expect(result.access_token).toBe('new-token');

    // Test 429 Too Many Requests
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: 'Quá nhiều lần thử thất bại',
          code: 'too_many_attempts',
        }),
        { status: 429 }
      )
    );

    await expect(performLogin({ username: 'user', password: 'pass' })).rejects.toMatchObject({
      status: 429,
      code: 'too_many_attempts',
    });
  });
});
