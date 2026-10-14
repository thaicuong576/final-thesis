import { useEffect, type ReactNode } from 'react';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { AUTH_EXPIRED_EVENT } from '@/shared/api/apiClient';

interface ProtectedRouteProps {
  children?: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { status, isAuthenticated, expiredNotice } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const handleExpired = () => {
      navigate('/login', {
        replace: true,
        state: { from: location, reason: 'expired' }
      });
    };
    if (typeof window !== 'undefined') {
      window.addEventListener(AUTH_EXPIRED_EVENT, handleExpired);
      return () => {
        window.removeEventListener(AUTH_EXPIRED_EVENT, handleExpired);
      };
    }
  }, [navigate, location]);

  if (status.isLoading) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-workspace text-ink"
        role="status"
        aria-label="Đang kiểm tra quyền truy cập"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="size-6 animate-spin rounded-full border-2 border-border-default border-t-amber" />
          <span className="text-xs text-ink-secondary">Đang tải...</span>
        </div>
      </div>
    );
  }

  if (status.required === false) {
    return children ? <>{children}</> : <Outlet />;
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{
          from: location,
          reason: expiredNotice ? 'expired' : undefined
        }}
        replace
      />
    );
  }

  return children ? <>{children}</> : <Outlet />;
}
