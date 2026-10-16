import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Sparkles, FileText, ArrowRight, Loader2, X } from 'lucide-react';
import { listFilingSamples } from '../api/filingService';
import { FILING_SAMPLES } from '@/test/fixtures/filingFixtures';
import type { FilingSample } from '../model/types';

interface SampleSelectorModalProps {
  open: boolean;
  onClose: () => void;
  onOpenSample: (sampleId: string) => Promise<void>;
}

export function SampleSelectorModal({
  open,
  onClose,
  onOpenSample,
}: SampleSelectorModalProps) {
  const [samples, setSamples] = useState<FilingSample[]>(FILING_SAMPLES);
  const [openingId, setOpeningId] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    listFilingSamples()
      .then((data) => {
        if (!cancelled && data && data.length > 0) {
          setSamples(data);
        }
      })
      .catch(() => {
        if (!cancelled) setSamples(FILING_SAMPLES);
      });

    return () => {
      cancelled = true;
    };
  }, [open]);

  const handleSelect = async (sampleId: string) => {
    setOpeningId(sampleId);
    try {
      await onOpenSample(sampleId);
      onClose();
    } finally {
      setOpeningId(null);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 animate-in fade-in-0"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sample-modal-title"
      data-testid="sample-selector-modal"
    >
      <div className="w-full max-w-lg rounded-md border border-line bg-card shadow-tactile p-5 space-y-4 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-text-accent" />
            <h3 id="sample-modal-title" className="text-sm font-bold text-ink">
              Chọn bộ mẫu báo cáo tài chính dựng sẵn
            </h3>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-7 w-7 p-0 text-ink-secondary hover:text-ink"
            aria-label="Đóng"
          >
            <X className="size-4" />
          </Button>
        </div>

        <p className="text-xs text-ink-secondary leading-relaxed">
          Bộ mẫu cho phép trình diễn trực tiếp các bước kiểm tra, xem trang đối chiếu và sửa số mà không cần tải lên tệp PDF hoặc chờ quét OCR.
        </p>

        <div className="space-y-2.5">
            {samples.map((s) => {
              const isOpening = openingId === s.sample_id;
              return (
                <div
                  key={s.sample_id}
                  className="rounded-md border border-line bg-surface-secondary/40 p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 hover:border-border-strong transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <FileText className="size-3.5 text-text-accent" />
                      <span className="font-bold text-xs text-ink">{s.title_vi}</span>
                    </div>
                    <p className="text-[11px] text-ink-secondary leading-relaxed">
                      {s.note_vi}
                    </p>
                    <div className="flex items-center gap-3 text-[11px] text-ink-tertiary font-mono">
                      <span>Mã: {s.entity_id}</span>
                      <span>Năm: {s.fiscal_year}</span>
                      <span>{s.page_count} trang</span>
                    </div>
                  </div>

                  <Button
                    type="button"
                    disabled={isOpening}
                    onClick={() => handleSelect(s.sample_id)}
                    className="h-8 border border-amber-border bg-amber text-ink hover:bg-amber-hover text-xs font-semibold px-3 shadow-tactile shrink-0"
                  >
                    {isOpening ? (
                      <>
                        <Loader2 className="mr-1 size-3 animate-spin" />
                        Đang mở…
                      </>
                    ) : (
                      <>
                        <span>Mở mẫu</span>
                        <ArrowRight className="ml-1 size-3" />
                      </>
                    )}
                  </Button>
                </div>
              );
            })}
          </div>

        <div className="border-t border-line pt-3 flex justify-end">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            className="h-8 border-line text-xs font-medium"
          >
            Đóng
          </Button>
        </div>
      </div>
    </div>
  );
}
