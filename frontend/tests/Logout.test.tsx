import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '../src/features/auth/AuthContext';
import { WorkspaceShell } from '../src/components/layout/WorkspaceShell';
import { saveSession, getSession } from '../src/features/auth/model/authStorage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

describe('Logout button', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('clears session and redirects to /login when clicking Đăng xuất', async () => {
    const user = userEvent.setup();

    saveSession({
      access_token: 'valid-session-token',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ required: true }), { status: 200 })
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/analysis']}>
            <Routes>
              <Route path="/login" element={<div>Màn hình Đăng Nhập Sau Đăng Xuất</div>} />
              <Route
                path="/analysis"
                element={
                  <WorkspaceShell activeSection="analysis">
                    <div>Nội dung phân tích</div>
                  </WorkspaceShell>
                }
              />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(screen.getByText('Nội dung phân tích')).toBeInTheDocument();

    const logoutButton = screen.getByRole('button', { name: 'Đăng xuất' });
    expect(logoutButton).toBeInTheDocument();

    await user.click(logoutButton);

    await waitFor(() => {
      expect(screen.getByText('Màn hình Đăng Nhập Sau Đăng Xuất')).toBeInTheDocument();
    });

    expect(getSession()).toBeNull();
  });
});
