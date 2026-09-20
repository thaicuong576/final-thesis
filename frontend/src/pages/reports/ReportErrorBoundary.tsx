import { Component, type ReactNode, type ErrorInfo } from 'react';
import { ReportErrorFallback } from './ReportErrorFallback';

interface ReportErrorBoundaryProps {
  children: ReactNode;
}

interface ReportErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ReportErrorBoundary extends Component<ReportErrorBoundaryProps, ReportErrorBoundaryState> {
  constructor(props: ReportErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ReportErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ReportErrorBoundary caught an error rendering report:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <ReportErrorFallback
          errorMessage="Đã xảy ra sự cố trong quá trình kết xuất dữ liệu chỉ tiêu tài chính của báo cáo."
          errorDetail={this.state.error?.message}
          onRetry={this.handleReset}
        />
      );
    }

    return this.props.children;
  }
}
