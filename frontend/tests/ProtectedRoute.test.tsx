import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from '../src/features/auth/AuthContext';
import { ProtectedRoute } from '../src/features/auth/ProtectedRoute';
import { saveSession, clearSession } from '../src/features/auth/model/authStorage';
import { dispatchAuthExpiredEvent } from '../src/shared/api/apiClient';

function MockLoginPage() {
  const location = useLocation();
  const state = location.state as { from?: { pathname: string }; reason?: string } | null;
  return (
    <div>
      <h1>Trang Đăng Nhập</h1>
      <span data-testid="redirect-from">{state?.from?.pathname || 'none'}</span>
      <span data-testid="redirect-reason">{state?.reason || 'none'}</span>
    </div>
  );
}

function MockProtectedPage() {
  return <div>Nội Dung Được Bảo Vệ</div>;
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    clearSession();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('bypasses login when auth is not required (required = false)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ required: false }), { status: 200 })
    );

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/analysis']}>
          <Routes>
            <Route path="/login" element={<MockLoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/analysis" element={<MockProtectedPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Nội Dung Được Bảo Vệ')).toBeInTheDocument();
    });
    expect(screen.queryByText('Trang Đăng Nhập')).not.toBeInTheDocument();
  });

  it('redirects to /login preserving target route when required = true and not logged in', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ required: true }), { status: 200 })
    );

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/reports/rep-123']}>
          <Routes>
            <Route path="/login" element={<MockLoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/reports/rep-123" element={<MockProtectedPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Trang Đăng Nhập')).toBeInTheDocument();
    });
    expect(screen.getByTestId('redirect-from')).toHaveTextContent('/reports/rep-123');
    expect(screen.queryByText('Nội Dung Được Bảo Vệ')).not.toBeInTheDocument();
  });

  it('allows access when required = true and valid session exists', async () => {
    saveSession({
      access_token: 'valid-token',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ required: true }), { status: 200 })
    );

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/data']}>
          <Routes>
            <Route path="/login" element={<MockLoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/data" element={<MockProtectedPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Nội Dung Được Bảo Vệ')).toBeInTheDocument();
    });
    expect(screen.queryByText('Trang Đăng Nhập')).not.toBeInTheDocument();
  });

  it('redirects to /login when AUTH_EXPIRED_EVENT is dispatched', async () => {
    saveSession({
      access_token: 'valid-token',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ required: true }), { status: 200 })
    );

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/data']}>
          <Routes>
            <Route path="/login" element={<MockLoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/data" element={<MockProtectedPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Nội Dung Được Bảo Vệ')).toBeInTheDocument();
    });

    // Simulate 401 token expiry event
    dispatchAuthExpiredEvent('Phiên đã hết hạn, vui lòng đăng nhập lại');

    await waitFor(() => {
      expect(screen.getByText('Trang Đăng Nhập')).toBeInTheDocument();
      expect(screen.getByTestId('redirect-reason')).toHaveTextContent('expired');
    });
  });
});
