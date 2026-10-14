import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  saveSession,
  getSession,
  clearSession,
  getToken,
  isSessionValid,
} from '../src/features/auth/model/authStorage';
import type { LoginResponse } from '../src/features/auth/model/types';

describe('authStorage', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.restoreAllMocks();
  });

  const validSession: LoginResponse = {
    access_token: 'fake-jwt-token-12345',
    token_type: 'bearer',
    expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
  };

  it('saves and retrieves a valid session', () => {
    saveSession(validSession);
    const retrieved = getSession();
    expect(retrieved).not.toBeNull();
    expect(retrieved?.access_token).toBe(validSession.access_token);
    expect(getToken()).toBe(validSession.access_token);
  });

  it('rejects an expired session and clears storage', () => {
    const expiredSession: LoginResponse = {
      access_token: 'expired-token',
      token_type: 'bearer',
      expires_at: new Date(Date.now() - 1000).toISOString(),
    };
    saveSession(expiredSession);

    const retrieved = getSession();
    expect(retrieved).toBeNull();
    expect(getToken()).toBeNull();
    expect(window.sessionStorage.getItem('thesis_auth_session')).toBeNull();
  });

  it('clears session properly', () => {
    saveSession(validSession);
    expect(getToken()).toBe(validSession.access_token);

    clearSession();
    expect(getSession()).toBeNull();
    expect(getToken()).toBeNull();
  });

  it('validates session timestamps with isSessionValid', () => {
    expect(isSessionValid(null)).toBe(false);
    expect(isSessionValid({ access_token: '', token_type: 'bearer', expires_at: '' })).toBe(false);
    expect(isSessionValid({ ...validSession, expires_at: 'invalid-date' })).toBe(false);
    expect(isSessionValid(validSession)).toBe(true);
  });

  it('survives sessionStorage throwing errors in restricted environments', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError');
    });

    expect(() => saveSession(validSession)).not.toThrow();
    expect(() => getSession()).not.toThrow();
    expect(getSession()).toBeNull();
    expect(() => clearSession()).not.toThrow();
  });
});
