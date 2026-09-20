import { Navigate, createBrowserRouter } from 'react-router-dom';
import { DataPage } from '../pages/data/DataPage';
import { CreateAnalysisPage } from '../pages/create-analysis/CreateAnalysisPage';
import { ReportPage } from '../pages/reports/ReportPage';

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
    element: <ReportPage />
  },
  {
    path: '/reports/:id',
    element: <ReportPage />
  }
]);
