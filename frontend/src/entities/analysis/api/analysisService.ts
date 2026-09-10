import type { AnalysisRequest, AnalysisSubmissionReceipt } from '../model/types';

export interface AnalysisService {
  submit(request: AnalysisRequest): Promise<AnalysisSubmissionReceipt>;
}

// Frontend-only confirmation. Replace with POST /api/analysis when the Python API is ready.
export const analysisService: AnalysisService = {
  async submit(request) {
    void request;
    return {
      accepted: true,
      requestId: 'frontend-validation-only',
      message: 'Yêu cầu đã vượt qua kiểm tra phía giao diện và sẵn sàng gửi đến backend.'
    };
  }
};
