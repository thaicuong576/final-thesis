import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Download,
  ArrowRight,
  Loader2,
  FileSpreadsheet,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getApiBaseUrl } from '@/shared/lib/apiUrl';

export interface OnboardingMetric {
  metric_id: string;
  computed_value: number;
  reported_value: number | null;
  status: string;
}

export interface OnboardingRowIssue {
  row: number | null;
  field: string | null;
  message_vi: string;
}

export interface OnboardingUploadResult {
  upload_id: string;
  entity_id: string;
  period_id: string;
  status: 'accepted' | 'rejected';
  display_name?: string | null;
  metrics: OnboardingMetric[];
  row_issues: OnboardingRowIssue[];
  limitations_vi: string[];
  created_at: string;
}

const METRIC_LABELS: Record<string, { label: string; unit: string }> = {
  'bank.npl_g35': { label: 'Tỷ lệ nợ xấu (NPL nhóm 3–5)', unit: '%' },
  'bank.llr_coverage': { label: 'Tỷ lệ bao phủ nợ xấu (LLR)', unit: '%' },
  'bank.roa': { label: 'Tỷ suất sinh lời trên tài sản (ROA)', unit: '%' },
  'bank.roe': { label: 'Tỷ suất sinh lời trên vốn CSH (ROE)', unit: '%' },
};

function formatMetricValue(val: number | null | undefined, unit: string): string {
  if (val === null || val === undefined) return '—';
  return `${val.toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${unit}`;
}

export function BankUploadSection() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [result, setResult] = useState<OnboardingUploadResult | null>(null);

  const apiBase = getApiBaseUrl();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
      setResult(null);
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
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.csv') || file.type.includes('csv') || file.type.includes('text')) {
        setSelectedFile(file);
        setUploadError(null);
        setResult(null);
      } else {
        setUploadError('Chỉ hỗ trợ tệp định dạng .csv');
      }
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await fetch(`${apiBase}/api/onboarding/uploads`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        let msg = `Lỗi tải lên (${res.status})`;
        try {
          const errData = await res.json();
          if (errData?.detail) {
            msg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
          }
        } catch {
          // ignore json parse error
        }
        setUploadError(msg);
        return;
      }

      const data: OnboardingUploadResult = await res.json();
      setResult(data);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Không thể kết nối tới dịch vụ tải lên');
    } finally {
      setIsUploading(false);
    }
  };

  const handleAskQuestion = useCallback(
    (questionText?: string) => {
      if (!result) return;
      const bank = result.entity_id;
      const defaultQ = `Tỷ lệ nợ xấu của ${bank} quý 4/2024 là bao nhiêu?`;
      const q = questionText || defaultQ;
      const params = new URLSearchParams({
        upload_id: result.upload_id,
        entity: bank,
        period: result.period_id,
        q,
      });
      navigate(`/analysis?${params.toString()}`);
    },
    [navigate, result]
  );

  return (
    <section className="w-full min-w-0 rounded-md border border-line bg-card p-4 sm:p-6" aria-labelledby="upload-heading">
      <div className="border-b border-line pb-4">
        <div className="flex items-center gap-2">
          <Upload className="size-4 text-ink-secondary shrink-0" aria-hidden="true" />
          <h2 id="upload-heading" className="text-base font-bold text-ink">
            Thêm ngân hàng mới từ tệp CSV
          </h2>
        </div>
        <p className="mt-1 text-xs text-ink-secondary leading-relaxed">
          Tải lên số liệu báo cáo tài chính đã đối chiếu của một ngân hàng chưa có trong bộ dữ liệu. Hệ thống kiểm tra cấu trúc tệp và vị trí nguồn, tự tính lại 4 chỉ tiêu, rồi cho phép hỏi về ngân hàng đó và so với nhóm ngân hàng sẵn có. Ngân hàng tải lên không được tính vào trung vị nhóm.
        </p>
      </div>

      {/* Action Bar: Download templates and sample files */}
      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
        <span className="font-semibold text-ink-secondary">Tệp mẫu &amp; dữ liệu kiểm thử:</span>
        <a
          href={`${apiBase}/api/onboarding/template.csv`}
          download="template.csv"
          className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface-secondary px-2.5 py-1 text-xs font-medium text-ink hover:bg-surface-hover no-underline transition-colors"
        >
          <Download className="size-3 text-ink-secondary" />
          Tải file mẫu (.csv)
        </a>
        <a
          href={`${apiBase}/api/onboarding/samples/vib-2025q4.csv`}
          download="vib-2025q4.csv"
          className="inline-flex items-center gap-1.5 rounded-md border border-ready/40 bg-ready-soft/40 px-2.5 py-1 text-xs font-medium text-text-success hover:bg-ready-soft/70 no-underline transition-colors"
        >
          <FileSpreadsheet className="size-3 text-ready" />
          Mẫu VIB 2025 hợp lệ
        </a>
        <a
          href={`${apiBase}/api/onboarding/samples/vib-2025q4-loi.csv`}
          download="vib-2025q4-loi.csv"
          className="inline-flex items-center gap-1.5 rounded-md border border-warning/40 bg-warning-soft/40 px-2.5 py-1 text-xs font-medium text-text-warning hover:bg-warning-soft/70 no-underline transition-colors"
        >
          <AlertTriangle className="size-3 text-warning" />
          Mẫu VIB có lỗi (thử nghiệm)
        </a>
      </div>

      {/* Upload Dropzone */}
      <div className="mt-5 space-y-4">
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
          aria-label="Vùng chọn tệp CSV tải lên"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            onChange={handleFileChange}
            className="hidden"
          />
          {selectedFile ? (
            <div className="space-y-1.5">
              <FileSpreadsheet className="mx-auto size-8 text-ready" />
              <div className="text-sm font-semibold text-ink">{selectedFile.name}</div>
              <div className="text-xs text-ink-secondary">
                {(selectedFile.size / 1024).toFixed(1)} KB · Nhấn để chọn tệp khác
              </div>
            </div>
          ) : (
            <div className="space-y-1.5">
              <Upload className="mx-auto size-8 text-ink-secondary" />
              <div className="text-sm font-semibold text-ink">
                Chọn hoặc kéo thả tệp CSV vào đây
              </div>
              <div className="text-xs text-ink-secondary">
                Định dạng CSV UTF-8, tối đa 200 dòng, kích thước &le; 256 KB
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-3">
          <div className="text-xs text-ink-secondary">
            {selectedFile
              ? `Đã chọn: ${selectedFile.name}`
              : 'Chưa chọn tệp'}
          </div>
          <Button
            type="button"
            disabled={!selectedFile || isUploading}
            onClick={handleSubmit}
            className="h-9 border border-amber-border bg-amber px-4 text-xs font-semibold text-ink shadow-tactile transition hover:bg-amber-hover active:translate-y-[0.5px] shrink-0 disabled:opacity-45 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {isUploading ? (
              <>
                <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                Đang kiểm tra &amp; tải lên…
              </>
            ) : (
              'Kiểm tra và tải lên'
            )}
          </Button>
        </div>

        {uploadError && (
          <div className="rounded-md border border-blocked/40 bg-blocked-soft/50 p-3 text-xs text-ink flex items-start gap-2.5">
            <XCircle className="size-4 text-blocked shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-blocked">Lỗi tải lên hoặc xác thực dữ liệu:</div>
              <div className="mt-0.5 leading-relaxed text-ink">{uploadError}</div>
            </div>
          </div>
        )}

        {/* Verification Result Card */}
        {result && (
          <div
            className={`mt-6 rounded-md border p-4 sm:p-5 space-y-4 ${
              result.status === 'accepted'
                ? 'border-ready/40 bg-ready-soft/20'
                : 'border-blocked/40 bg-blocked-soft/20'
            }`}
            data-testid="upload-result-card"
          >
            {/* Status Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-line pb-3">
              <div className="flex items-center gap-2">
                {result.status === 'accepted' ? (
                  <CheckCircle2 className="size-5 text-ready shrink-0" />
                ) : (
                  <XCircle className="size-5 text-blocked shrink-0" />
                )}
                <div>
                  <h3 className="text-sm font-bold text-ink">
                    {result.status === 'accepted'
                      ? `Đã xác thực và chấp nhận: ${result.entity_id} (${result.period_id})`
                      : `Từ chối tiếp nhận tệp: ${result.entity_id || 'Ngân hàng mới'}`}
                  </h3>
                  <p className="text-xs text-ink-secondary font-mono">
                    Mã phiên tải lên: {result.upload_id}
                  </p>
                </div>
              </div>

              {result.status === 'accepted' && (
                <Button
                  type="button"
                  onClick={() => handleAskQuestion()}
                  className="h-8 border border-amber-border bg-amber px-3 text-xs font-semibold text-ink shadow-tactile transition hover:bg-amber-hover active:translate-y-[0.5px] shrink-0"
                >
                  <span>Hỏi về {result.entity_id}</span>
                  <ArrowRight className="ml-1 size-3.5" />
                </Button>
              )}
            </div>

            {/* Recomputed Metrics Table */}
            {result.metrics && result.metrics.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-bold uppercase tracking-wide text-ink-secondary">
                  Kết quả kiểm tra &amp; tái tính toán chỉ tiêu tài chính
                </div>
                <div className="overflow-x-auto rounded border border-line bg-card">
                  <table className="w-full min-w-[500px] border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-line bg-surface-secondary text-ink-secondary">
                        <th className="py-2 px-3 font-semibold">Chỉ tiêu</th>
                        <th className="py-2 px-3 text-right font-semibold">Giá trị tính lại</th>
                        <th className="py-2 px-3 text-right font-semibold">Giá trị công bố</th>
                        <th className="py-2 px-3 text-center font-semibold">Trạng thái</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {result.metrics.map((m) => {
                        const info = METRIC_LABELS[m.metric_id] || { label: m.metric_id, unit: '%' };
                        const isMatch = m.status === 'valid';
                        return (
                          <tr key={m.metric_id} className="hover:bg-surface-hover/40 transition-colors">
                            <td className="py-2 px-3">
                              <span className="font-semibold text-ink">{info.label}</span>
                              <span className="block font-mono text-[11px] text-ink-secondary">
                                {m.metric_id}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-right font-mono font-medium text-ink">
                              {formatMetricValue(m.computed_value, info.unit)}
                            </td>
                            <td className="py-2 px-3 text-right font-mono text-ink-secondary">
                              {formatMetricValue(m.reported_value, info.unit)}
                            </td>
                            <td className="py-2 px-3 text-center">
                              {isMatch ? (
                                <span className="inline-flex items-center rounded-full bg-ready-soft px-2 py-0.5 text-[11px] font-medium text-text-success border border-ready/30">
                                  Hợp lệ
                                </span>
                              ) : (
                                <span className="inline-flex items-center rounded-full bg-blocked-soft px-2 py-0.5 text-[11px] font-medium text-blocked border border-blocked/30">
                                  Lệch dung sai
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Row Issues */}
            {result.row_issues && result.row_issues.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-bold uppercase tracking-wide text-blocked flex items-center gap-1.5">
                  <AlertTriangle className="size-3.5 text-blocked" />
                  Danh sách lỗi dữ liệu phát hiện ({result.row_issues.length}):
                </div>
                <div className="rounded-md border border-blocked/30 bg-blocked-soft/30 p-3 space-y-1.5 text-xs">
                  {result.row_issues.map((issue, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-ink leading-relaxed">
                      <span className="font-mono font-semibold shrink-0 text-blocked">
                        {issue.row ? `Dòng ${issue.row}` : 'Cấu trúc'}:
                      </span>
                      <span>{issue.message_vi}</span>
                      {issue.field && (
                        <span className="font-mono text-[11px] text-blocked">({issue.field})</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Limitations Notice */}
            {result.limitations_vi && result.limitations_vi.length > 0 && (
              <div className="rounded-md border border-warning/40 bg-warning-soft/40 p-3 text-xs text-ink space-y-1">
                <div className="font-semibold text-text-warning flex items-center gap-1.5">
                  <FileText className="size-3.5 text-warning" />
                  Giới hạn sử dụng dữ liệu:
                </div>
                {result.limitations_vi.map((lim, idx) => (
                  <p key={idx} className="leading-relaxed text-ink-secondary">
                    {lim}
                  </p>
                ))}
              </div>
            )}

            {/* Suggested Questions when Accepted */}
            {result.status === 'accepted' && (
              <div className="pt-2 border-t border-line space-y-2">
                <div className="text-xs font-semibold text-ink">Gợi ý câu hỏi phân tích cho {result.entity_id}:</div>
                <div className="flex flex-col gap-1.5 text-xs">
                  {[
                    `Tỷ lệ nợ xấu của ${result.entity_id} quý 4/2024 là bao nhiêu?`,
                    `Hồ sơ tài chính của ${result.entity_id} trong năm 2024`,
                    `So sánh nợ xấu giữa ${result.entity_id} và ACB trong quý 4/2024`,
                  ].map((qText, qIdx) => (
                    <button
                      key={qIdx}
                      type="button"
                      onClick={() => handleAskQuestion(qText)}
                      className="text-left text-ink hover:text-text-accent hover:underline py-0.5 cursor-pointer flex items-center gap-1.5 transition-colors"
                    >
                      <ArrowRight className="size-3 text-amber-border shrink-0" />
                      <span>{qText}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
