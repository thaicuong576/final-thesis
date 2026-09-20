import { Navigate, createBrowserRouter } from 'react-router-dom';
import { DataPage } from '../pages/data/DataPage';
import { CreateAnalysisPage } from '../pages/create-analysis/CreateAnalysisPage';
import { ReportPage } from '../pages/reports/ReportPage';
import { ReportsListPage } from '../pages/reports/ReportsListPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/analysis" replace />
  },
  {
    path: '/analysis',
    element: <CreateAnalysisPage />
  },
  {
    path: '/data',
    element: <DataPage />
  },
  {
    path: '/analysis/new',
    element: <Navigate to="/analysis" replace />
  },
  {
    path: '/reports',
    element: <ReportsListPage />
  },
  {
    path: '/reports/:id',
    element: <ReportPage />
  }
]);
