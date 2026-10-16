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
      return 'Máy chủ chưa có công cụ OCR (Tesseract). Bạn có thể chọn "Dùng bộ mẫu dựng sẵn" để xem ngay quy trình hướng dẫn mà không cần chạy OCR thực.';
    case 'not_a_pdf':
      return 'Tệp tải lên không phải định dạng PDF hợp lệ. Vui lòng kiểm tra lại tệp.';
    case 'encrypted':
      return 'Tệp PDF có mật khẩu bảo vệ hoặc bị khóa mã hóa. Hãy mở khóa tệp trước khi tải lên.';
    case 'no_statements_found':
      return 'Không nhận diện được trang Bảng cân đối kế toán hoặc Báo cáo kết quả kinh doanh trong tài liệu. Hãy chọn tệp báo cáo tài chính đầy đủ.';
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
        className="rounded-md border border-blocked/40 bg-blocked-soft/30 p-5 space-y-4"
        role="alert"
        data-testid="processing-failed"
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="size-5 text-blocked shrink-0 mt-0.5" aria-hidden="true" />
          <div className="space-y-1.5 flex-1">
            <h3 className="text-sm font-bold text-blocked">
              Quá trình đọc báo cáo tài chính không thành công
            </h3>
            <p className="text-xs text-ink leading-relaxed">
              {errorMessage || 'Đã xảy ra lỗi trong quá trình đọc và trích xuất dữ liệu.'}
            </p>
            <div className="rounded border border-blocked/20 bg-card p-3 text-xs text-ink-secondary mt-2">
              <span className="font-semibold text-ink block mb-0.5">Hướng xử lý khuyến nghị:</span>
              <span>{errorResolutionAdvice(errorCode)}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-line">
          {onRetry && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onRetry}
              className="h-8 border-line text-xs font-semibold gap-1.5"
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
              className="h-8 border border-amber-border bg-amber text-ink hover:bg-amber-hover text-xs font-semibold gap-1.5 shadow-tactile"
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
      className="rounded-md border border-line bg-card p-6 space-y-4 shadow-tactile"
      data-testid="processing-step"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Loader2 className="size-5 animate-spin text-amber-border" aria-hidden="true" />
          <div>
            <h3 className="text-sm font-bold text-ink">Đang đọc và trích xuất báo cáo tài chính</h3>
            <p className="text-xs text-ink-secondary">
              Hệ thống quét từng trang, phân loại các bảng tài chính và trích xuất số liệu ứng viên.
            </p>
          </div>
        </div>
        <span className="font-mono text-sm font-bold text-text-accent tabular-nums">
          {percent}%
        </span>
      </div>

      {/* Progress bar with accessibility */}
      <div
        className="w-full bg-surface-secondary rounded-full h-3 overflow-hidden border border-line"
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

      {/* Progress info and polling notice */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 text-xs text-ink-secondary pt-1">
        <div className="flex items-center gap-2">
          <BookOpen className="size-3.5 text-text-accent" />
          <span className="font-medium text-ink">
            Đang đọc trang {progress.pages_done}/{progress.page_count || '…'}
          </span>
        </div>
        <div>
          <span>Nguồn đọc: </span>
          <span className="font-semibold text-ink">{ocrProviderLabel(ocrProvider)}</span>
        </div>
      </div>

      <p className="text-[11px] text-ink-tertiary italic">
        Trạng thái được cập nhật tự động mỗi 2 giây. Vui lòng không đóng trang.
      </p>
    </div>
  );
}
