import { createContext, useContext } from 'react';
import type { LoginCredentials, LoginResponse } from './model/types';

export interface AuthStatusState {
  required: boolean | null;
  isLoading: boolean;
  error: Error | null;
}

export interface AuthContextValue {
  status: AuthStatusState;
  isAuthenticated: boolean;
  session: LoginResponse | null;
  expiredNotice: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  clearExpiredNotice: () => void;
  checkStatus: () => Promise<void>;
}

export const defaultAuthContext: AuthContextValue = {
  status: { required: false, isLoading: false, error: null },
  isAuthenticated: true,
  session: null,
  expiredNotice: null,
  login: async () => {},
  logout: () => {},
  clearExpiredNotice: () => {},
  checkStatus: async () => {},
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  return context ?? defaultAuthContext;
}
