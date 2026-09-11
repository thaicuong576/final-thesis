import { Navigate, createBrowserRouter } from 'react-router-dom';
import { DataPage } from '../pages/data/DataPage';
import { CreateAnalysisPage } from '../pages/create-analysis/CreateAnalysisPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/data" replace />
  },
  {
    path: '/data',
    element: <DataPage />
  },
  {
    path: '/analysis/new',
    element: <CreateAnalysisPage />
  }
  // Reserved routes (/analysis/:runId, /reports/:reportId, /research) are intentionally
  // not registered until their product surfaces are designed and implemented.
]);
