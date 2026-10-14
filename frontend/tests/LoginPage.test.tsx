import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '../src/features/auth/AuthContext';
import { LoginPage } from '../src/pages/login/LoginPage';
import { clearSession, getSession } from '../src/features/auth/model/authStorage';

describe('LoginPage', () => {
  beforeEach(() => {
    clearSession();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders login form elements and supports toggling password visibility', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ required: true }), { status: 200 })
    );

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    );

    expect(screen.getByLabelText('Tên đăng nhập')).toBeInTheDocument();
    expect(screen.getByLabelText('Mật khẩu')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Đăng nhập' })).toBeInTheDocument();

    const passwordInput = screen.getByLabelText('Mật khẩu');
    expect(passwordInput).toHaveAttribute('type', 'password');

    const toggleButton = screen.getByLabelText('Hiện mật khẩu');
    await userEvent.click(toggleButton);

    expect(passwordInput).toHaveAttribute('type', 'text');
    expect(screen.getByLabelText('Ẩn mật khẩu')).toBeInTheDocument();
  });

  it('handles successful login and redirects to target route', async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ required: true }), { status: 200 })) // auth status
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: 'valid-jwt-token',
            token_type: 'bearer',
            expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
          }),
          { status: 200 }
        )
      ); // login

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={[{ pathname: '/login', state: { from: { pathname: '/reports' } } }]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/reports" element={<div>Trang Báo Cáo Thành Công</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await user.type(screen.getByLabelText('Tên đăng nhập'), 'analyst');
    await user.type(screen.getByLabelText('Mật khẩu'), 'secret123');
    await user.click(screen.getByRole('button', { name: 'Đăng nhập' }));

    await waitFor(() => {
      expect(screen.getByText('Trang Báo Cáo Thành Công')).toBeInTheDocument();
    });

    const session = getSession();
    expect(session?.access_token).toBe('valid-jwt-token');
  });

  it('displays Vietnamese error message on invalid credentials (401)', async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ required: true }), { status: 200 })) // status
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ detail: 'Invalid credentials', code: 'invalid_credentials' }),
          { status: 401 }
        )
      ); // login 401

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    );

    await user.type(screen.getByLabelText('Tên đăng nhập'), 'analyst');
    await user.type(screen.getByLabelText('Mật khẩu'), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: 'Đăng nhập' }));

    await waitFor(() => {
      expect(screen.getByText('Tên đăng nhập hoặc mật khẩu không chính xác.')).toBeInTheDocument();
    });
  });

  it('displays rate limit error on 429 too_many_attempts', async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ required: true }), { status: 200 })) // status
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ detail: 'Quá nhiều lần thử', code: 'too_many_attempts' }),
          { status: 429 }
        )
      ); // login 429

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    );

    await user.type(screen.getByLabelText('Tên đăng nhập'), 'analyst');
    await user.type(screen.getByLabelText('Mật khẩu'), 'any');
    await user.click(screen.getByRole('button', { name: 'Đăng nhập' }));

    await waitFor(() => {
      expect(screen.getByText('Quá nhiều lần thử thất bại. Vui lòng thử lại sau ít phút.')).toBeInTheDocument();
    });
  });

  it('displays offline network error when fetch fails', async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ required: true }), { status: 200 })) // status
      .mockRejectedValueOnce(new TypeError('Failed to fetch')); // login network failure

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    );

    await user.type(screen.getByLabelText('Tên đăng nhập'), 'analyst');
    await user.type(screen.getByLabelText('Mật khẩu'), 'any');
    await user.click(screen.getByRole('button', { name: 'Đăng nhập' }));

    await waitFor(() => {
      expect(screen.getByText('Không thể kết nối đến máy chủ. Vui lòng kiểm tra đường truyền.')).toBeInTheDocument();
    });
  });

  it('bypasses login and redirects to /analysis when required = false', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ required: false }), { status: 200 })
    );

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/analysis" element={<div>Trang Phân Tích Chính</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Trang Phân Tích Chính')).toBeInTheDocument();
    });
  });
});
