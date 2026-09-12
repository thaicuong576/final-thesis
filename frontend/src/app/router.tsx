import { Navigate, createBrowserRouter } from 'react-router-dom';
import { DataPage } from '../pages/data/DataPage';
import { CreateAnalysisPage } from '../pages/create-analysis/CreateAnalysisPage';
import { ReportsPlaceholderPage } from '../pages/reports/ReportsPlaceholderPage';
import { WorkflowMonitorPage } from '../pages/workflow/WorkflowMonitorPage';

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
    path: '/analysis/:runId',
    element: <WorkflowMonitorPage />
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
    element: <ReportsPlaceholderPage />
  }
  // Reserved routes (/reports/:reportId, /research) are intentionally
  // not registered until their product surfaces are designed and implemented.
]);
