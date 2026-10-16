import { Loader2, AlertCircle, RefreshCw, Sparkles, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { FilingErrorCode, FilingProgress, OcrProvider } from '../model/types';

interface ProcessingStepProps {
  progress: FilingProgress;
  ocrProvider: OcrProvider;
  isFailed: boolean;
  errorCode?: FilingErrorCode;
  errorMessage?: string;
  onRetry?: () => void;
  onUseSample?: () => void;
}

function ocrProviderLabel(provider: OcrProvider): string {
  switch (provider) {
    case 'text_layer':
      return 'Lớp chữ có sẵn trong PDF';
    case 'tesseract':
      return 'Công cụ nhận diện ký tự Tesseract OCR';
    case 'llamaparse':
      return 'Dịch vụ trích xuất LlamaParse';
    case 'sample':
      return 'Bộ dữ liệu mẫu dựng sẵn';
    case 'mixed':
      return 'Hỗn hợp (chữ có sẵn và OCR)';
    default:
      return 'Tự động nhận diện';
  }
}

function errorResolutionAdvice(code?: FilingErrorCode): string {
  switch (code) {
    case 'ocr_unavailable':
      return 'Máy chủ chưa có công cụ OCR (Tesseract). Bạn có thể chọn "Dùng bộ mẫu dựng sẵn để trình diễn" để xem quy trình mà không cần quét OCR thực.';
    case 'not_a_pdf':
      return 'Tệp tải lên không phải định dạng PDF hợp lệ. Vui lòng kiểm tra lại tệp.';
    case 'encrypted':
      return 'Tệp PDF có mật khẩu bảo vệ hoặc bị khóa mã hóa. Hãy mở khóa tệp trước khi tải lên.';
    case 'no_statements_found':
      return 'Không nhận diện được trang Bảng cân đối kế toán hoặc Báo cáo kết quả kinh doanh trong tài liệu.';
    case 'provider_error':
    default:
      return 'Có lỗi kết nối hoặc xử lý từ phía dịch vụ trích xuất. Hãy thử lại sau.';
  }
}

export function ProcessingStep({
  progress,
  ocrProvider,
  isFailed,
  errorCode,
  errorMessage,
  onRetry,
  onUseSample,
}: ProcessingStepProps) {
  const percent =
    progress.page_count > 0
      ? Math.min(100, Math.round((progress.pages_done / progress.page_count) * 100))
      : 0;

  if (isFailed) {
    return (
      <div
        className="rounded-md border border-line bg-card p-4 space-y-3"
        role="alert"
        data-testid="processing-failed"
      >
        <div className="flex items-start gap-2.5">
          <AlertCircle className="size-4 text-blocked shrink-0 mt-0.5" aria-hidden="true" />
          <div className="space-y-1 flex-1 text-xs">
            <h3 className="font-bold text-blocked">
              Quá trình đọc báo cáo tài chính không thành công
            </h3>
            <p className="text-ink leading-relaxed">
              {errorMessage || 'Đã xảy ra lỗi trong quá trình đọc và trích xuất dữ liệu.'}
            </p>
            <p className="text-ink-secondary pt-0.5">
              <span className="font-semibold text-ink">Hướng xử lý khuyến nghị: </span>
              {errorResolutionAdvice(errorCode)}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-line">
          {onRetry && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onRetry}
              className="h-7 border-line text-xs font-medium gap-1.5"
            >
              <RefreshCw className="size-3" />
              Thử tải lại tệp khác
            </Button>
          )}
          {onUseSample && (
            <Button
              type="button"
              size="sm"
              onClick={onUseSample}
              className="h-7 border border-amber-border bg-amber text-ink hover:bg-amber-hover text-xs font-semibold gap-1.5 shadow-sm"
            >
              <Sparkles className="size-3" />
              Dùng bộ mẫu dựng sẵn để trình diễn
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className="rounded-md border border-line bg-card p-4 space-y-3"
      data-testid="processing-step"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Loader2 className="size-4 animate-spin text-amber-border" aria-hidden="true" />
          <div>
            <h3 className="text-xs font-bold text-ink">Đang đọc và trích xuất báo cáo tài chính</h3>
            <p className="text-[11px] text-ink-secondary">
              Quét tài liệu, nhận diện bảng và trích xuất 10 chỉ tiêu đầu vào.
            </p>
          </div>
        </div>
        <span className="font-mono text-xs font-bold text-ink tabular-nums">
          {percent}%
        </span>
      </div>

      {/* Progress bar */}
      <div
        className="w-full bg-surface-secondary rounded-full h-2 overflow-hidden border border-line"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Tiến độ đọc báo cáo tài chính"
      >
        <div
          className="bg-amber h-full transition-all duration-300 rounded-full"
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Progress info */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 text-[11px] text-ink-secondary pt-0.5">
        <div className="flex items-center gap-1.5">
          <BookOpen className="size-3 text-ink-tertiary" />
          <span>
            Đang đọc trang {progress.pages_done}/{progress.page_count || '…'}
          </span>
        </div>
        <div>
          <span>Nguồn đọc: </span>
          <span className="font-medium text-ink">{ocrProviderLabel(ocrProvider)}</span>
        </div>
      </div>
    </div>
  );
}
