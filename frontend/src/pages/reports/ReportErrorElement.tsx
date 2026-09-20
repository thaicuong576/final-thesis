import { useRouteError, isRouteErrorResponse } from 'react-router-dom';
import { ReportErrorFallback } from './ReportErrorFallback';

export function ReportErrorElement() {
  const error = useRouteError();

  let errorMessage = 'Đã xảy ra sự cố trong quá trình kết xuất dữ liệu chỉ tiêu tài chính của báo cáo.';
  let errorDetail = '';

  if (isRouteErrorResponse(error)) {
    errorMessage = error.statusText || errorMessage;
    errorDetail = typeof error.data === 'string' ? error.data : JSON.stringify(error.data);
  } else if (error instanceof Error) {
    errorDetail = error.message;
  } else if (typeof error === 'string') {
    errorDetail = error;
  }

  return (
    <ReportErrorFallback
      errorMessage={errorMessage}
      errorDetail={errorDetail}
    />
  );
}
