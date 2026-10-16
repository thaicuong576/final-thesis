import { useState } from 'react';
import { Loader2, RefreshCw, ZoomIn, ZoomOut, FileImage, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { filingPageImageUrl } from '../api/filingService';

interface PageImageViewerProps {
  filingId: string;
  pageNumber: number | null;
  onClose?: () => void;
  className?: string;
}

export function PageImageViewer({
  filingId,
  pageNumber,
  onClose,
  className = '',
}: PageImageViewerProps) {
  const [zoom, setZoom] = useState<number>(100);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [hasError, setHasError] = useState<boolean>(false);
  const [reloadKey, setReloadKey] = useState<number>(0);

  if (!pageNumber) {
    return (
      <div
        className={`flex flex-col items-center justify-center rounded-md border border-line bg-surface-secondary/40 p-6 text-center text-xs text-ink-secondary ${className}`}
      >
        <FileImage className="size-8 text-ink-tertiary mb-2" aria-hidden="true" />
        <p className="font-medium text-ink">Chưa chọn trang để xem</p>
        <p className="mt-1 text-[11px] text-ink-tertiary">
          Nhấn vào số trang ở bảng số liệu hoặc danh sách trang để xem ảnh gốc đối chiếu.
        </p>
      </div>
    );
  }

  const imageUrl = `${filingPageImageUrl(filingId, pageNumber)}?k=${reloadKey}`;

  const handleRetry = () => {
    setHasError(false);
    setIsLoading(true);
    setReloadKey((k) => k + 1);
  };

  return (
    <div
      className={`flex flex-col rounded-md border border-line bg-card overflow-hidden shadow-tactile ${className}`}
      data-testid="page-image-viewer"
    >
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-line bg-surface-secondary px-3 py-2 text-xs">
        <div className="flex items-center gap-2">
          <FileImage className="size-3.5 text-text-accent" aria-hidden="true" />
          <span className="font-semibold text-ink">Trang {pageNumber} (Ảnh tài liệu gốc)</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setZoom((z) => Math.max(50, z - 25))}
            className="h-7 w-7 p-0 text-ink-secondary hover:text-ink"
            title="Thu nhỏ"
            aria-label="Thu nhỏ ảnh"
          >
            <ZoomOut className="size-3.5" />
          </Button>
          <span className="font-mono text-[11px] text-ink-secondary min-w-[36px] text-center">
            {zoom}%
          </span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setZoom((z) => Math.min(200, z + 25))}
            className="h-7 w-7 p-0 text-ink-secondary hover:text-ink"
            title="Phóng to"
            aria-label="Phóng to ảnh"
          >
            <ZoomIn className="size-3.5" />
          </Button>
          {onClose && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-7 w-7 p-0 text-ink-secondary hover:text-ink ml-1"
              title="Đóng"
              aria-label="Đóng khung xem ảnh"
            >
              <X className="size-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Image container */}
      <div className="relative flex-1 min-h-[360px] max-h-[640px] overflow-auto bg-neutral-900/5 p-3 flex items-center justify-center">
        {isLoading && !hasError && (
          <div
            className="absolute inset-0 flex flex-col items-center justify-center bg-card/75 gap-2 z-10"
            role="status"
          >
            <Loader2 className="size-6 animate-spin text-amber-border" aria-hidden="true" />
            <span className="text-xs text-ink-secondary">Đang tải ảnh trang {pageNumber}…</span>
          </div>
        )}

        {hasError ? (
          <div className="flex flex-col items-center justify-center p-6 text-center text-xs space-y-3">
            <p className="font-semibold text-blocked">Không tải được ảnh trang {pageNumber}</p>
            <p className="text-ink-secondary max-w-[240px]">
              Tệp ảnh trang có thể chưa được kết xuất hoặc máy chủ đang xử lý.
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleRetry}
              className="h-8 border-line text-xs font-semibold gap-1.5"
            >
              <RefreshCw className="size-3" />
              Thử tải lại
            </Button>
          </div>
        ) : (
          <img
            key={imageUrl}
            src={imageUrl}
            alt={`Ảnh trang ${pageNumber} báo cáo tài chính`}
            onLoad={() => {
              setIsLoading(false);
              setHasError(false);
            }}
            onError={() => {
              setIsLoading(false);
              setHasError(true);
            }}
            style={{ width: `${zoom}%`, maxWidth: 'none' }}
            className="rounded border border-line bg-white shadow-sm transition-all duration-150 select-none object-contain"
          />
        )}
      </div>

      <div className="border-t border-line bg-surface-secondary/60 px-3 py-1.5 text-[11px] text-ink-tertiary flex items-center justify-between">
        <span>Độ phân giải 120 DPI</span>
        <span>Đối chiếu số liệu cột 31.12</span>
      </div>
    </div>
  );
}
