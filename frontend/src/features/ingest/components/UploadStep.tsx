import { useState, useRef } from 'react';
import {
  Upload,
  AlertCircle,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface UploadStepProps {
  onStartUpload: (
    file: File,
    meta: {
      entity_id: string;
      fiscal_year: number;
      reporting_scope: 'consolidated' | 'separate';
      display_name?: string;
    }
  ) => Promise<void>;
  onOpenSampleModal: () => void;
  isUploading: boolean;
  uploadError: string | null;
}

export function UploadStep({
  onStartUpload,
  onOpenSampleModal,
  isUploading,
  uploadError,
}: UploadStepProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [entityId, setEntityId] = useState<string>('');
  const [fiscalYear, setFiscalYear] = useState<number>(2025);
  const [reportingScope, setReportingScope] = useState<'consolidated' | 'separate' | ''>('');
  const [formError, setFormError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      if (!f.name.toLowerCase().endsWith('.pdf')) {
        setFormError('Chỉ hỗ trợ tệp định dạng PDF (.pdf).');
        return;
      }
      setSelectedFile(f);
      setFormError(null);

      // Auto-extract bank code hint from filename if possible (e.g. "ACB_FY2025.pdf" -> ACB)
      const match = f.name.match(/^([A-Za-z]{3})[_ -]/);
      if (match && !entityId) {
        setEntityId(match[1].toUpperCase());
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const f = e.dataTransfer.files[0];
      if (!f.name.toLowerCase().endsWith('.pdf')) {
        setFormError('Chỉ hỗ trợ tệp định dạng PDF (.pdf).');
        return;
      }
      setSelectedFile(f);
      setFormError(null);

      const match = f.name.match(/^([A-Za-z]{3})[_ -]/);
      if (match && !entityId) {
        setEntityId(match[1].toUpperCase());
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!selectedFile) {
      setFormError('Vui lòng chọn hoặc kéo thả tệp PDF báo cáo tài chính.');
      return;
    }

    const cleanEntityId = entityId.trim().toUpperCase();
    if (!cleanEntityId || cleanEntityId.length < 3) {
      setFormError('Mã ngân hàng bắt buộc có ít nhất 3 ký tự viết hoa (ví dụ: ACB, VCB, MBB).');
      return;
    }

    if (!fiscalYear || fiscalYear < 2010 || fiscalYear > 2030) {
      setFormError('Năm tài chính không hợp lệ (ví dụ: 2025).');
      return;
    }

    if (!reportingScope) {
      setFormError('Bắt buộc chọn phạm vi báo cáo: Báo cáo hợp nhất hoặc Báo cáo riêng lẻ.');
      return;
    }

    await onStartUpload(selectedFile, {
      entity_id: cleanEntityId,
      fiscal_year: Number(fiscalYear),
      reporting_scope: reportingScope,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3.5" data-testid="upload-step-form">
      {/* Quiet Dropzone */}
      <div className="space-y-1.5 text-center">
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`flex items-center justify-center gap-2.5 rounded-md border border-dashed py-4 px-4 transition-colors cursor-pointer text-xs ${
            isDragging
              ? 'border-amber bg-amber-soft/20'
              : selectedFile
              ? 'border-ready/60 bg-ready-soft/10 text-ink'
              : 'border-line hover:border-ink-tertiary bg-surface-secondary/30 hover:bg-surface-secondary/60 text-ink-secondary'
          }`}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          aria-label="Vùng chọn tệp PDF báo cáo tài chính"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            className="hidden"
            aria-label="Tải lên tệp PDF"
          />
          {selectedFile ? (
            <>
              <CheckCircle2 className="size-4 text-ready shrink-0" />
              <span className="font-semibold text-ink truncate max-w-sm">{selectedFile.name}</span>
              <span className="text-ink-tertiary text-[11px]">
                ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
              </span>
              <span className="text-text-accent text-[11px] underline ml-1">Đổi tệp</span>
            </>
          ) : (
            <>
              <Upload className="size-4 text-ink-secondary shrink-0" />
              <span className="text-ink">
                Chọn hoặc kéo thả báo cáo tài chính năm (PDF)
              </span>
            </>
          )}
        </div>

        <div>
          <button
            type="button"
            aria-label="Dùng bộ mẫu dựng sẵn"
            onClick={onOpenSampleModal}
            className="text-xs text-text-accent hover:underline cursor-pointer transition-colors"
          >
            hoặc dùng bộ mẫu
          </button>
        </div>
      </div>

      {/* 3 Plain Fields in 1 Row on Desktop */}
      <div className="grid grid-cols-1 sm:grid-cols-[1fr_110px_auto] items-end gap-3 pt-1">
        {/* Bank code */}
        <div>
          <label htmlFor="input-entity-id" className="block text-xs font-semibold text-ink mb-1">
            Mã ngân hàng
          </label>
          <Input
            id="input-entity-id"
            type="text"
            maxLength={10}
            value={entityId}
            onChange={(e) => setEntityId(e.target.value.toUpperCase())}
            placeholder="Ví dụ: ACB"
            className="h-8 font-mono text-xs uppercase bg-card"
            required
          />
        </div>

        {/* Fiscal Year */}
        <div>
          <label htmlFor="input-fiscal-year" className="block text-xs font-semibold text-ink mb-1">
            Năm tài chính
          </label>
          <Input
            id="input-fiscal-year"
            type="number"
            min={2015}
            max={2030}
            value={fiscalYear}
            onChange={(e) => setFiscalYear(Number(e.target.value))}
            className="h-8 font-mono text-xs bg-card"
            required
          />
        </div>

        {/* Scope Segmented Control */}
        <div>
          <span className="block text-xs font-semibold text-ink mb-1">
            Phạm vi lập báo cáo
          </span>
          <div
            className="inline-flex h-8 rounded border border-line bg-surface-secondary p-0.5"
            role="radiogroup"
            aria-label="Phạm vi lập báo cáo"
          >
            <label
              className={`inline-flex items-center px-2.5 rounded text-xs font-semibold cursor-pointer transition-colors select-none ${
                reportingScope === 'consolidated'
                  ? 'bg-amber text-ink shadow-sm'
                  : 'text-ink-secondary hover:text-ink'
              }`}
            >
              <input
                type="radio"
                name="reporting-scope"
                value="consolidated"
                checked={reportingScope === 'consolidated'}
                onChange={() => setReportingScope('consolidated')}
                className="sr-only"
                aria-label="Báo cáo hợp nhất"
              />
              <span>Báo cáo hợp nhất</span>
            </label>

            <label
              className={`inline-flex items-center px-2.5 rounded text-xs font-semibold cursor-pointer transition-colors select-none ${
                reportingScope === 'separate'
                  ? 'bg-amber text-ink shadow-sm'
                  : 'text-ink-secondary hover:text-ink'
              }`}
            >
              <input
                type="radio"
                name="reporting-scope"
                value="separate"
                checked={reportingScope === 'separate'}
                onChange={() => setReportingScope('separate')}
                className="sr-only"
                aria-label="Báo cáo riêng lẻ"
              />
              <span>Báo cáo riêng lẻ</span>
            </label>
          </div>
        </div>
      </div>

      {/* Error alert */}
      {(formError || uploadError) && (
        <div className="text-xs text-blocked flex items-center gap-1.5 pt-0.5">
          <AlertCircle className="size-3.5 shrink-0" />
          <span>{formError || uploadError}</span>
        </div>
      )}

      {/* Action Button */}
      <div className="flex justify-end pt-1">
        <Button
          type="submit"
          disabled={!selectedFile || !reportingScope || isUploading}
          className="h-8 border border-amber-border bg-amber px-4 text-xs font-semibold text-ink shadow-tactile hover:bg-amber-hover transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isUploading ? (
            <>
              <Loader2 className="mr-1.5 size-3.5 animate-spin" />
              Đang tải lên và trích xuất…
            </>
          ) : (
            'Bắt đầu đọc và trích xuất PDF'
          )}
        </Button>
      </div>
    </form>
  );
}
