import { useState, useRef } from 'react';
import {
  Upload,
  AlertCircle,
  Loader2,
  Sparkles,
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
  const [displayName, setDisplayName] = useState<string>('');
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
      display_name: displayName.trim() || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" data-testid="upload-step-form">
      {/* File Dropzone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`flex flex-col items-center justify-center rounded-md border-2 border-dashed p-6 transition-colors cursor-pointer text-center ${
          isDragging
            ? 'border-amber-border bg-amber-soft/30'
            : selectedFile
            ? 'border-ready/60 bg-ready-soft/20'
            : 'border-line hover:border-border-strong bg-surface-secondary/40 hover:bg-surface-hover/40'
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
          <div className="space-y-1.5">
            <CheckCircle2 className="mx-auto size-8 text-ready" />
            <div className="text-sm font-semibold text-ink">{selectedFile.name}</div>
            <div className="text-xs text-ink-secondary">
              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB · Nhấn để chọn tệp khác
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            <Upload className="mx-auto size-8 text-ink-secondary" />
            <div className="text-sm font-semibold text-ink">
              Chọn hoặc kéo thả báo cáo tài chính (PDF) vào đây
            </div>
            <div className="text-xs text-ink-secondary">
              Định dạng PDF, dung lượng tối đa 40 MB. Hỗ trợ cả bản scan không có lớp chữ.
            </div>
          </div>
        )}
      </div>

      {/* Scope banner / Notice */}
      <div className="rounded border border-line bg-surface-secondary/60 px-3.5 py-2 text-xs text-ink-secondary flex items-center justify-between">
        <span className="font-medium text-ink">
          Phạm vi v1: Báo cáo tài chính năm đã kiểm toán
        </span>
        <span className="text-[11px] text-ink-tertiary">
          (Báo cáo giữa niên độ và quý nằm ngoài phạm vi v1)
        </span>
      </div>

      {/* Metadata Inputs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Bank code */}
        <div>
          <label htmlFor="input-entity-id" className="block text-xs font-semibold text-ink mb-1">
            Mã ngân hàng (3 chữ) <span className="text-blocked">*</span>
          </label>
          <Input
            id="input-entity-id"
            type="text"
            maxLength={10}
            value={entityId}
            onChange={(e) => setEntityId(e.target.value.toUpperCase())}
            placeholder="Ví dụ: ACB"
            className="h-8 font-mono text-xs uppercase bg-white"
            required
          />
        </div>

        {/* Fiscal Year */}
        <div>
          <label htmlFor="input-fiscal-year" className="block text-xs font-semibold text-ink mb-1">
            Năm tài chính <span className="text-blocked">*</span>
          </label>
          <Input
            id="input-fiscal-year"
            type="number"
            min={2015}
            max={2030}
            value={fiscalYear}
            onChange={(e) => setFiscalYear(Number(e.target.value))}
            className="h-8 font-mono text-xs bg-white"
            required
          />
        </div>

        {/* Display name */}
        <div>
          <label htmlFor="input-display-name" className="block text-xs font-semibold text-ink mb-1">
            Tên hiển thị (tùy chọn)
          </label>
          <Input
            id="input-display-name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Ví dụ: Ngân hàng Á Châu"
            className="h-8 text-xs bg-white"
          />
        </div>
      </div>

      {/* Reporting Scope (Mandatory, No default!) */}
      <div>
        <label className="block text-xs font-semibold text-ink mb-1.5">
          Phạm vi lập báo cáo <span className="text-blocked">* (bắt buộc chọn)</span>
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          <label
            className={`flex items-start gap-2.5 rounded-md border p-2.5 cursor-pointer transition-colors ${
              reportingScope === 'consolidated'
                ? 'border-amber bg-amber-soft/30'
                : 'border-line hover:border-border-strong bg-card'
            }`}
          >
            <input
              type="radio"
              name="reporting-scope"
              value="consolidated"
              checked={reportingScope === 'consolidated'}
              onChange={() => setReportingScope('consolidated')}
              className="mt-0.5 size-3.5 text-amber focus:ring-amber-border cursor-pointer"
            />
            <div>
              <span className="block text-xs font-bold text-ink">Báo cáo hợp nhất</span>
              <span className="block text-[11px] text-ink-secondary mt-0.5">
                Bao gồm ngân hàng mẹ và các công ty con liên kết
              </span>
            </div>
          </label>

          <label
            className={`flex items-start gap-2.5 rounded-md border p-2.5 cursor-pointer transition-colors ${
              reportingScope === 'separate'
                ? 'border-amber bg-amber-soft/30'
                : 'border-line hover:border-border-strong bg-card'
            }`}
          >
            <input
              type="radio"
              name="reporting-scope"
              value="separate"
              checked={reportingScope === 'separate'}
              onChange={() => setReportingScope('separate')}
              className="mt-0.5 size-3.5 text-amber focus:ring-amber-border cursor-pointer"
            />
            <div>
              <span className="block text-xs font-bold text-ink">Báo cáo riêng lẻ</span>
              <span className="block text-[11px] text-ink-secondary mt-0.5">
                Chỉ riêng hoạt động của pháp nhân ngân hàng mẹ
              </span>
            </div>
          </label>
        </div>
      </div>

      {/* Error alert */}
      {(formError || uploadError) && (
        <div className="rounded-md border border-blocked/40 bg-blocked-soft/40 p-3 text-xs text-ink flex items-start gap-2.5">
          <AlertCircle className="size-4 text-blocked shrink-0 mt-0.5" />
          <div className="leading-relaxed font-medium text-blocked">
            {formError || uploadError}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2 border-t border-line">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onOpenSampleModal}
          className="h-9 border-line text-xs font-semibold text-ink gap-1.5 self-start sm:self-auto"
        >
          <Sparkles className="size-3.5 text-text-accent" />
          Dùng bộ mẫu dựng sẵn (Trình diễn)
        </Button>

        <Button
          type="submit"
          disabled={!selectedFile || !reportingScope || isUploading}
          className="h-9 border border-amber-border bg-amber px-4 text-xs font-semibold text-ink shadow-tactile hover:bg-amber-hover transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        >
          {isUploading ? (
            <>
              <Loader2 className="mr-1.5 size-3.5 animate-spin" />
              Đang tải lên và khởi động đọc…
            </>
          ) : (
            'Bắt đầu đọc và trích xuất PDF'
          )}
        </Button>
      </div>
    </form>
  );
}
