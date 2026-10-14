import { useState, type FormEvent, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { BarChart3, Eye, EyeOff, Lock, AlertCircle, Info, Loader2 } from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function LoginPage() {
  const { login, isAuthenticated, status, expiredNotice, clearExpiredNotice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Determine return target
  const from = (location.state as { from?: { pathname: string; search?: string } })?.from;
  const redirectTarget = from ? `${from.pathname}${from.search || ''}` : '/analysis';

  // If auth is not required or already authenticated, redirect to target
  useEffect(() => {
    if (!status.isLoading && (status.required === false || isAuthenticated)) {
      navigate(redirectTarget, { replace: true });
    }
  }, [status.isLoading, status.required, isAuthenticated, navigate, redirectTarget]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrorMessage('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    clearExpiredNotice();

    try {
      await login({ username: username.trim(), password });
      navigate(redirectTarget, { replace: true });
    } catch (err: unknown) {
      const error = err as { status?: number; code?: string; message?: string };
      if (error.status === 401) {
        setErrorMessage('Tên đăng nhập hoặc mật khẩu không chính xác.');
      } else if (error.status === 429 || error.code === 'too_many_attempts') {
        setErrorMessage('Quá nhiều lần thử thất bại. Vui lòng thử lại sau ít phút.');
      } else if (
        error.message?.includes('Failed to fetch') ||
        error.message?.includes('NetworkError') ||
        error.message?.includes('network') ||
        error.message?.includes('mất kết nối')
      ) {
        setErrorMessage('Không thể kết nối đến máy chủ. Vui lòng kiểm tra đường truyền.');
      } else {
        setErrorMessage(error.message || 'Đăng nhập không thành công. Vui lòng thử lại.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-workspace p-4 text-ink paper-grid">
      <div className="w-full max-w-sm">
        {/* Brand header */}
        <div className="mb-6 flex flex-col items-center text-center">
          <div
            className="mb-3 grid size-12 place-items-center rounded-xl bg-amber text-ink shadow-tactile"
            aria-hidden="true"
          >
            <BarChart3 className="size-6 stroke-[2.2]" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-ink">Phân tích tài chính</h1>
          <p className="mt-1 text-xs text-ink-secondary">Ngân hàng niêm yết Việt Nam</p>
        </div>

        {/* Login form card */}
        <div className="rounded-xl border border-border-default bg-surface-primary p-6 shadow-tactile sm:p-7">
          <div className="mb-5 flex items-center justify-between border-b border-border-subtle pb-3">
            <span className="text-sm font-semibold text-ink">Đăng nhập hệ thống</span>
            <span className="flex items-center gap-1 font-mono text-[11px] text-ink-secondary">
              <Lock className="size-3" aria-hidden="true" />
              Bảo mật
            </span>
          </div>

          {/* Session expired notice */}
          {expiredNotice && (
            <Alert className="mb-4 border-amber-border bg-accent-soft text-ink" role="alert">
              <Info className="size-4 text-amber-active" />
              <AlertDescription className="text-xs font-medium text-ink">
                {expiredNotice}
              </AlertDescription>
            </Alert>
          )}

          {/* Error notice */}
          {errorMessage && (
            <Alert variant="destructive" className="mb-4" role="alert">
              <AlertCircle className="size-4" />
              <AlertDescription className="text-xs font-medium">
                {errorMessage}
              </AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label
                htmlFor="username"
                className="mb-1.5 block text-xs font-medium text-ink"
              >
                Tên đăng nhập
              </label>
              <Input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                autoFocus
                disabled={isSubmitting}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Nhập tên đăng nhập"
                className="h-9 bg-surface-secondary text-sm border-border-default focus-visible:ring-amber"
                required
              />
            </div>

            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="block text-xs font-medium text-ink"
                >
                  Mật khẩu
                </label>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  disabled={isSubmitting}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Nhập mật khẩu"
                  className="h-9 bg-surface-secondary pr-9 text-sm border-border-default focus-visible:ring-amber"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-secondary transition-colors hover:text-ink focus:outline-none"
                  tabIndex={0}
                >
                  {showPassword ? (
                    <EyeOff className="size-4 stroke-[1.8]" />
                  ) : (
                    <Eye className="size-4 stroke-[1.8]" />
                  )}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="mt-2 w-full text-sm font-semibold"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  <span>Đang đăng nhập...</span>
                </>
              ) : (
                'Đăng nhập'
              )}
            </Button>
          </form>

          <div className="mt-5 border-t border-border-subtle pt-3 text-center">
            <p className="text-[11px] text-ink-secondary">
              Cổng truy cập bảo mật · Dành cho chuyên viên phân tích
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
