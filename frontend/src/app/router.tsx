import { Navigate, createBrowserRouter } from 'react-router-dom';
import { DataPage } from '../pages/data/DataPage';
import { CreateAnalysisPage } from '../pages/create-analysis/CreateAnalysisPage';
import { ReportPage } from '../pages/reports/ReportPage';
import { ReportsListPage } from '../pages/reports/ReportsListPage';
import { RouteErrorElement } from './RouteErrorElement';
import { SourceLineageDemo } from '../features/source-lineage';
import { LoginPage } from '../pages/login/LoginPage';
import { ProtectedRoute } from '../features/auth/ProtectedRoute';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
    errorElement: <RouteErrorElement section="analysis" />
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/',
        element: <Navigate to="/analysis" replace />,
        errorElement: <RouteErrorElement section="analysis" />
      },
      {
        path: '/analysis',
        element: <CreateAnalysisPage />,
        errorElement: <RouteErrorElement section="analysis" />
      },
      {
        path: '/session',
        element: <CreateAnalysisPage initialMode="SESSION" />,
        errorElement: <RouteErrorElement section="analysis" />
      },
      {
        path: '/data',
        element: <DataPage />,
        errorElement: <RouteErrorElement section="data" />
      },
      {
        path: '/analysis/new',
        element: <Navigate to="/analysis" replace />
      },
      {
        path: '/reports',
        element: <ReportsListPage />,
        errorElement: <RouteErrorElement section="reports" />
      },
      {
        path: '/reports/:id',
        element: <ReportPage />,
        errorElement: <RouteErrorElement section="reports" />
      },
      ...(import.meta.env.DEV
        ? [
            {
              path: '/demo/lineage',
              element: <SourceLineageDemo />,
            },
          ]
        : []),
    ]
  }
]);
