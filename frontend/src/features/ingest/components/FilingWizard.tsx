import { useState, useEffect, useRef } from 'react';
import {
  FileText,
  CheckCircle2,
  RotateCcw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UploadStep } from './UploadStep';
import { ProcessingStep } from './ProcessingStep';
import { StatementPagesChips } from './StatementPagesChips';
import { ExtractedRowsTable } from './ExtractedRowsTable';
import { ValidationPanel } from './ValidationPanel';
import { PageImageViewer } from './PageImageViewer';
import { ConfirmationStep } from './ConfirmationStep';
import { SampleSelectorModal } from './SampleSelectorModal';
import {
  createFiling,
  getFiling,
  updateRow,
  confirmFiling,
  openFilingSample,
} from '../api/filingService';
import type { ConfirmResult, Filing } from '../model/types';

export interface FilingWizardProps {
  initialFiling?: Filing | null;
  onFilingConfirmed?: (result: ConfirmResult) => void;
}

export function FilingWizard({ initialFiling = null, onFilingConfirmed }: FilingWizardProps) {
  const [filing, setFiling] = useState<Filing | null>(initialFiling);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [selectedPage, setSelectedPage] = useState<number | null>(null);
  const [highlightedRowIds, setHighlightedRowIds] = useState<string[]>([]);
  const [isConfirming, setIsConfirming] = useState<boolean>(false);
  const [confirmResult, setConfirmResult] = useState<ConfirmResult | null>(null);
  const [isSampleModalOpen, setIsSampleModalOpen] = useState<boolean>(false);

  // Active page to view
  const activePage =
    selectedPage ??
    filing?.statement_pages?.balance_sheet?.[0] ??
    filing?.rows?.find((r) => r.page !== null)?.page ??
    1;

  // Collapsed step toggles
  const [isUploadCollapsed, setIsUploadCollapsed] = useState<boolean>(false);

  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Poll filing status when processing
  useEffect(() => {
    if (!filing || filing.status !== 'processing') {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
      return;
    }

    const poll = async () => {
      try {
        const updated = await getFiling(filing.filing_id);
        setFiling(updated);
        if (updated.status === 'ready' && !selectedPage) {
          const firstPage =
            updated.statement_pages.balance_sheet[0] ||
            updated.statement_pages.income_statement[0] ||
            updated.rows[0]?.page ||
            1;
          setSelectedPage(firstPage);
        }
      } catch {
        // If API fails (e.g. offline testing), keep current state
      }
    };

    pollingTimerRef.current = setInterval(poll, 2000);

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [filing, selectedPage]);

  // Handler: Start upload
  const handleStartUpload = async (
    file: File,
    meta: {
      entity_id: string;
      fiscal_year: number;
      reporting_scope: 'consolidated' | 'separate';
      display_name?: string;
    }
  ) => {
    setIsUploading(true);
    setUploadError(null);
    try {
      const resp = await createFiling(file, meta);
      setFiling({
        filing_id: resp.filing_id,
        status: 'processing',
        filename: file.name,
        sha256: '',
        page_count: 0,
        entity_id: meta.entity_id,
        display_name: meta.display_name || meta.entity_id,
        fiscal_year: meta.fiscal_year,
        reporting_scope: meta.reporting_scope,
        ocr_provider: 'tesseract',
        progress: { pages_done: 0, page_count: 0 },
        statement_pages: { balance_sheet: [], income_statement: [], loan_quality_note: [] },
        unit_detected: null,
        rows: [],
        validation: {
          status: 'fail',
          ready_to_confirm: false,
          blocking_reasons_vi: ['Đang đọc tệp'],
          checks: [],
        },
        limitations_vi: [],
      });
      setIsUploadCollapsed(true);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Lỗi tải lên tệp PDF');
    } finally {
      setIsUploading(false);
    }
  };

  // Handler: Open sample
  const handleOpenSample = async (sampleId: string) => {
    try {
      const sampleFiling = await openFilingSample(sampleId);
      setFiling(sampleFiling);
      setIsUploadCollapsed(true);
      setConfirmResult(null);
      if (sampleFiling.statement_pages.balance_sheet[0]) {
        setSelectedPage(sampleFiling.statement_pages.balance_sheet[0]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Lỗi mở mẫu filing';
      setUploadError(msg);
    }
  };

  // Handler: Update row (edit or toggle confirm)
  const handleUpdateRow = async (rowId: string, value: string | null, confirmed: boolean) => {
    if (!filing) return;

    try {
      const resp = await updateRow(filing.filing_id, rowId, {
        value_billion_vnd: value,
        confirmed,
      });

      setFiling((prev) => {
        if (!prev) return null;
        const newRows = prev.rows.map((r) => (r.row_id === rowId ? resp.row : r));
        return {
          ...prev,
          rows: newRows,
          validation: resp.validation,
        };
      });
    } catch {
      // Offline fallback: update optimistically
      setFiling((prev) => {
        if (!prev) return null;
        const newRows = prev.rows.map((r) => {
          if (r.row_id !== rowId) return r;
          const wasEdited = value !== r.extracted_value_billion_vnd;
          return {
            ...r,
            value_billion_vnd: value,
            confirmed,
            edited: wasEdited || r.edited,
            status: (confirmed ? 'candidate' : r.status) as Filing['rows'][0]['status'],
          };
        });

        const hasUnconfirmed = newRows.some((r) => !r.confirmed);
        const hasMissing = newRows.some((r) => r.value_billion_vnd === null);
        const ready = !hasUnconfirmed && !hasMissing;

        return {
          ...prev,
          rows: newRows,
          validation: {
            ...prev.validation,
            ready_to_confirm: ready,
            blocking_reasons_vi: ready ? [] : ['Còn dòng chưa được xác nhận đầy đủ'],
          },
        };
      });
    }
  };

  // Handler: Confirm filing
  const handleConfirm = async () => {
    if (!filing) return;
    setIsConfirming(true);
    setUploadError(null);
    try {
      const result = await confirmFiling(filing.filing_id);
      setConfirmResult(result);
      if (onFilingConfirmed) onFilingConfirmed(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Lỗi xác nhận filing';
      setUploadError(msg);
    } finally {
      setIsConfirming(false);
    }
  };

  // Handler: Reset wizard
  const handleReset = () => {
    setFiling(null);
    setSelectedPage(null);
    setHighlightedRowIds([]);
    setConfirmResult(null);
    setIsUploadCollapsed(false);
    setUploadError(null);
  };

  return (
    <section
      className="w-full min-w-0 rounded-md border border-line bg-card p-4 sm:p-5 space-y-5 scroll-mt-16"
      aria-labelledby="filing-wizard-heading"
      data-testid="filing-wizard-section"
    >
      {/* Header */}
      <div className="border-b border-line pb-3 flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="size-4 text-text-accent shrink-0" aria-hidden="true" />
            <h2 id="filing-wizard-heading" className="text-sm font-bold text-ink">
              Thêm ngân hàng từ báo cáo tài chính PDF
            </h2>
          </div>
          <p className="text-xs text-ink-secondary mt-1">
            Trích xuất và kiểm tra 10 chỉ tiêu tài chính từ tài liệu PDF trước khi nạp vào phân tích.
          </p>
        </div>

        {filing && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="h-7 text-xs font-medium text-ink-secondary hover:text-ink gap-1 self-start sm:self-auto shrink-0"
          >
            <RotateCcw className="size-3" />
            Làm lại từ đầu
          </Button>
        )}
      </div>

      {/* STEP 1: Upload (collapses into one quiet line when complete) */}
      <div className="space-y-1.5">
        {!isUploadCollapsed && (
          <div className="text-xs font-semibold text-ink">Bước 1: Tải lên tài liệu PDF</div>
        )}

        {isUploadCollapsed && filing ? (
          <div className="flex flex-wrap items-center justify-between gap-2 py-2 px-3 rounded border border-line bg-surface-secondary/40 text-xs">
            <div className="flex items-center gap-2 min-w-0">
              <CheckCircle2 className="size-4 text-ready shrink-0" />
              <span className="font-semibold text-ink truncate max-w-xs">{filing.filename}</span>
              <span className="text-ink-secondary">
                · {filing.entity_id} ({filing.fiscal_year}) · {filing.reporting_scope === 'consolidated' ? 'Hợp nhất' : 'Riêng lẻ'}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setIsUploadCollapsed(false)}
              className="text-[11px] font-semibold text-text-accent hover:underline shrink-0 cursor-pointer"
            >
              Đổi tệp khác
            </button>
          </div>
        ) : (
          <UploadStep
            onStartUpload={handleStartUpload}
            onOpenSampleModal={() => setIsSampleModalOpen(true)}
            isUploading={isUploading}
            uploadError={uploadError}
          />
        )}
      </div>

      {/* STEP 2: Processing (only rendered while processing or failed) */}
      {filing && (filing.status === 'processing' || filing.status === 'failed') && (
        <div className="space-y-2 pt-2 border-t border-line">
          <div className="text-xs font-semibold text-ink">Bước 2: Đang đọc và quét OCR</div>
          <ProcessingStep
            progress={filing.progress}
            ocrProvider={filing.ocr_provider}
            isFailed={filing.status === 'failed'}
            errorCode={filing.error_code}
            errorMessage={filing.message_vi}
            onRetry={handleReset}
            onUseSample={() => setIsSampleModalOpen(true)}
          />
        </div>
      )}

      {/* STEP 3: Review & Confirmation (only rendered when ready) */}
      {filing && filing.status === 'ready' && (
        <div className="space-y-5 pt-1 border-t border-line">
          {/* Statement Pages Links */}
          <StatementPagesChips
            pages={filing.statement_pages}
            selectedPage={activePage}
            onSelectPage={setSelectedPage}
          />

          {/* Main workspace: Extracted Rows Table + Page Image Viewer */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            <div className="lg:col-span-7 space-y-4">
              <ExtractedRowsTable
                rows={filing.rows}
                onUpdateRow={handleUpdateRow}
                onSelectPage={setSelectedPage}
                selectedPage={activePage}
                highlightedRowIds={highlightedRowIds}
              />
            </div>

            <div className="lg:col-span-5 lg:sticky lg:top-4">
              <PageImageViewer
                filingId={filing.filing_id}
                pageNumber={activePage}
                onClose={() => setSelectedPage(null)}
              />
            </div>
          </div>

          {/* Validation Block */}
          <ValidationPanel
            validation={filing.validation}
            onHighlightRows={(rowIds) => {
              setHighlightedRowIds(rowIds);
              const matchedRow = filing.rows.find((r) => rowIds.includes(r.row_id) && r.page);
              if (matchedRow?.page) setSelectedPage(matchedRow.page);
            }}
            highlightedRowIds={highlightedRowIds}
          />

          {/* Confirmation Step */}
          <ConfirmationStep
            readyToConfirm={filing.validation.ready_to_confirm}
            isConfirming={isConfirming}
            onConfirm={handleConfirm}
            confirmResult={confirmResult}
            entityId={filing.entity_id}
          />
        </div>
      )}

      {/* Sample Selector Modal */}
      <SampleSelectorModal
        open={isSampleModalOpen}
        onClose={() => setIsSampleModalOpen(false)}
        onOpenSample={handleOpenSample}
      />
    </section>
  );
}
