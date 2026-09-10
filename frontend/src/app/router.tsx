import { Navigate, createBrowserRouter } from 'react-router-dom';
import { CreateAnalysisPage } from '../pages/create-analysis/CreateAnalysisPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/analysis/new" replace />
  },
  {
    path: '/analysis/new',
    element: <CreateAnalysisPage />
  }
  // Reserved routes (/analysis/:runId, /reports/:reportId, /research) are intentionally
  // not registered until their product surfaces are designed and implemented.
]);
