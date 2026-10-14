import { getApiBaseUrl } from '@/shared/lib/apiUrl';
import { clearSession, getToken } from '@/features/auth/model/authStorage';
import type { AuthStatusResponse, LoginCredentials, LoginResponse } from '@/features/auth/model/types';

export const AUTH_EXPIRED_EVENT = 'thesis:auth:expired';

export interface AuthExpiredDetail {
  message: string;
}

export function dispatchAuthExpiredEvent(message = 'Phiên đã hết hạn, vui lòng đăng nhập lại'): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent<AuthExpiredDetail>(AUTH_EXPIRED_EVENT, {
        detail: { message }
      })
    );
  }
}

export function resolveApiUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) {
    return pathOrUrl;
  }
  const base = getApiBaseUrl();
  const normalizedPath = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`;
  return base ? `${base}${normalizedPath}` : normalizedPath;
}

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  let urlString = '';
  if (typeof input === 'string') {
    urlString = input;
  } else if (input instanceof URL) {
    urlString = input.toString();
  } else if (typeof Request !== 'undefined' && input instanceof Request) {
    urlString = input.url;
  }

  const isApiRequest = urlString.includes('/api/');
  const isLoginEndpoint = urlString.includes('/api/auth/login');

  let headers = init.headers || (typeof input === 'object' && input !== null && 'headers' in input ? (input as Request).headers : undefined);

  if (isApiRequest) {
    const token = getToken();
    if (token) {
      if (typeof Headers !== 'undefined' && headers instanceof Headers) {
        if (!headers.has('Authorization')) {
          headers.set('Authorization', `Bearer ${token}`);
        }
      } else if (Array.isArray(headers)) {
        if (!headers.some(([k]) => k.toLowerCase() === 'authorization')) {
          headers = [...headers, ['Authorization', `Bearer ${token}`]];
        }
      } else {
        headers = {
          ...headers,
          Authorization: `Bearer ${token}`,
        };
      }
    }
  }

  const resolvedInput = typeof input === 'string' && input.startsWith('/api/')
    ? resolveApiUrl(input)
    : input;

  const fetchInit: RequestInit = {
    ...init,
    ...(headers !== undefined ? { headers } : {})
  };

  const response = await fetch(resolvedInput, fetchInit);

  if (response.status === 401 && !isLoginEndpoint) {
    clearSession();
    dispatchAuthExpiredEvent();
  }

  return response;
}

export async function fetchAuthStatus(): Promise<AuthStatusResponse> {
  const response = await apiFetch('/api/auth/status', {
    headers: { Accept: 'application/json' }
  });
  if (!response.ok) {
    throw new Error(`Không thể kiểm tra trạng thái xác thực (HTTP ${response.status}).`);
  }
  return (await response.json()) as AuthStatusResponse;
}

export async function performLogin(credentials: LoginCredentials): Promise<LoginResponse> {
  const response = await apiFetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json'
    },
    body: JSON.stringify(credentials)
  });

  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as { detail?: string; code?: string };
    const error = new Error(
      errorData.detail || (response.status === 401 ? 'Tên đăng nhập hoặc mật khẩu không chính xác.' : 'Đăng nhập thất bại.')
    ) as Error & { status: number; code?: string };
    error.status = response.status;
    error.code = errorData.code;
    throw error;
  }

  return (await response.json()) as LoginResponse;
}
