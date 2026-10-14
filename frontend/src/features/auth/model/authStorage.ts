import type { LoginResponse } from './types';

const AUTH_STORAGE_KEY = 'thesis_auth_session';

export function isSessionValid(session: LoginResponse | null): boolean {
  if (!session || !session.access_token || !session.expires_at) {
    return false;
  }
  try {
    const expiresMs = new Date(session.expires_at).getTime();
    if (Number.isNaN(expiresMs)) {
      return false;
    }
    // Check if token expiration is still in the future (with 5 second leeway)
    return expiresMs > Date.now() + 5000;
  } catch {
    return false;
  }
}

export function saveSession(session: LoginResponse): void {
  try {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
    }
  } catch {
    // Gracefully handle environments where sessionStorage is restricted
  }
}

export function getSession(): LoginResponse | null {
  try {
    if (typeof window === 'undefined' || !window.sessionStorage) {
      return null;
    }
    const raw = window.sessionStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const session = JSON.parse(raw) as LoginResponse;
    if (!isSessionValid(session)) {
      clearSession();
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  const session = getSession();
  return session ? session.access_token : null;
}

export function clearSession(): void {
  try {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      window.sessionStorage.removeItem(AUTH_STORAGE_KEY);
    }
  } catch {
    // Gracefully handle storage exceptions
  }
}
