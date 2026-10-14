import { useEffect, useState, useCallback, useMemo, type ReactNode } from 'react';
import { clearSession, getSession, isSessionValid, saveSession } from './model/authStorage';
import type { LoginCredentials, LoginResponse } from './model/types';
import { AUTH_EXPIRED_EVENT, fetchAuthStatus, performLogin, type AuthExpiredDetail } from '@/shared/api/apiClient';
import { AuthContext, type AuthContextValue, type AuthStatusState } from './useAuth';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<LoginResponse | null>(() => getSession());
  const [status, setStatus] = useState<AuthStatusState>({
    required: null,
    isLoading: true,
    error: null,
  });
  const [expiredNotice, setExpiredNotice] = useState<string | null>(null);

  const checkStatus = useCallback(async () => {
    try {
      const res = await fetchAuthStatus();
      setStatus({
        required: res.required,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setStatus({
        required: false,
        isLoading: false,
        error,
      });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadStatus() {
      try {
        const res = await fetchAuthStatus();
        if (!cancelled) {
          setStatus({
            required: res.required,
            isLoading: false,
            error: null,
          });
        }
      } catch (err) {
        if (!cancelled) {
          const error = err instanceof Error ? err : new Error(String(err));
          setStatus({
            required: false,
            isLoading: false,
            error,
          });
        }
      }
    }
    void loadStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  // Listen for session expiry events from apiClient
  useEffect(() => {
    const handleExpired = (event: Event) => {
      const customEvent = event as CustomEvent<AuthExpiredDetail>;
      setSession(null);
      setExpiredNotice(customEvent.detail?.message || 'Phiên đã hết hạn, vui lòng đăng nhập lại');
    };

    if (typeof window !== 'undefined') {
      window.addEventListener(AUTH_EXPIRED_EVENT, handleExpired);
      return () => {
        window.removeEventListener(AUTH_EXPIRED_EVENT, handleExpired);
      };
    }
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    const res = await performLogin(credentials);
    saveSession(res);
    setSession(res);
    setExpiredNotice(null);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setSession(null);
    setExpiredNotice(null);
  }, []);

  const clearExpiredNotice = useCallback(() => {
    setExpiredNotice(null);
  }, []);

  // When required is false, user is always considered authenticated
  const isAuthenticated = status.required === false ? true : isSessionValid(session);

  const value: AuthContextValue = useMemo(() => ({
    status,
    isAuthenticated,
    session,
    expiredNotice,
    login,
    logout,
    clearExpiredNotice,
    checkStatus,
  }), [status, isAuthenticated, session, expiredNotice, login, logout, clearExpiredNotice, checkStatus]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
