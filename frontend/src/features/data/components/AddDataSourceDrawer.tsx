import { useEffect, useRef, useState, type ReactNode } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronLeft,
  FileSpreadsheet,
  FileText,
  Link2,
  Server,
  X,
  type LucideIcon
} from 'lucide-react';
import { cn } from '../../../shared/lib/cn';

interface AddDataSourceDrawerProps {
  open: boolean;
  onClose: () => void;
  onCreated: (name: string) => void;
}

type SourceType = 'CSV / Excel' | 'Database' | 'API' | 'Tài liệu';

const sourceOptions: Array<{ label: SourceType; description: string; icon: LucideIcon }> = [
  { label: 'CSV / Excel', description: 'Tệp bảng dữ liệu', icon: FileSpreadsheet },
  { label: 'Database', description: 'Kết nối nguồn dữ liệu', icon: Server },
  { label: 'API', description: 'Nguồn dữ liệu tích hợp', icon: Link2 },
  { label: 'Tài liệu', description: 'Báo cáo và văn bản', icon: FileText }
];

const steps = ['Nguồn', 'Nhận diện dữ liệu', 'Kiểm tra', 'Xác nhận'];

export function AddDataSourceDrawer({ open, onClose, onCreated }: AddDataSourceDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [sourceType, setSourceType] = useState<SourceType>('CSV / Excel');
  const [mappingEditing, setMappingEditing] = useState(false);
  const [showWarnings, setShowWarnings] = useState(false);
  const [datasetName, setDatasetName] = useState('Ngân hàng Việt Nam 2024');

  useEffect(() => {
    if (!open) return;
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus();

    function getFocusableElements() {
      const dialog = closeButtonRef.current?.closest('[role="dialog"]');
      if (!dialog) return [];
      return [...dialog.querySelectorAll<HTMLElement>('button, input, select, textarea, [tabindex]:not([tabindex="-1"])')]
        .filter((element) => !element.hasAttribute('disabled'));
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = getFocusableElements();
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [onClose, open]);

  if (!open) return null;

  function handleNext() {
    if (currentStep < steps.length) {
      setCurrentStep((step) => step + 1);
      return;
    }
    onCreated(datasetName.trim() || 'Bộ dữ liệu mới');
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50" role="presentation">
      <button type="button" aria-label="Đóng thêm nguồn dữ liệu" className="absolute inset-0 cursor-default bg-ink/30" onClick={onClose} />
      <aside
        className="absolute right-0 top-0 flex h-full w-full max-w-[560px] flex-col border-l border-line bg-canvas shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-source-title"
        tabIndex={-1}
      >
        <header className="flex items-start justify-between border-b border-line bg-white px-6 py-5">
          <div>
            <h2 id="add-source-title" className="font-display text-[28px] font-semibold leading-tight text-ink">Thêm nguồn dữ liệu</h2>
            <p className="mt-1 text-xs leading-5 text-muted">Tạo một bộ dữ liệu có thể sử dụng trong phân tích.</p>
          </div>
          <button ref={closeButtonRef} type="button" aria-label="Đóng" onClick={onClose} className="rounded-sm p-2 text-muted transition hover:bg-selected hover:text-ink">
            <X size={20} aria-hidden="true" />
          </button>
        </header>

        <nav aria-label="Các bước thêm nguồn dữ liệu" className="border-b border-line bg-white px-6 py-4">
          <ol className="grid grid-cols-4 gap-2">
            {steps.map((step, index) => {
              const stepNumber = index + 1;
              const complete = stepNumber < currentStep;
              const active = stepNumber === currentStep;
              return (
                <li key={step} className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={cn('grid h-6 w-6 shrink-0 place-items-center border text-[11px] font-semibold', {
                      'border-[#1c5d9c] bg-[#1c5d9c] text-white': active,
                      'border-[#8db6d9] bg-[#edf5fb] text-[#1c5d9c]': complete,
                      'border-line bg-white text-muted': !active && !complete
                    })}>
                      {complete ? <Check size={13} aria-hidden="true" /> : stepNumber}
                    </span>
                    <span className={cn('truncate text-[11px] font-semibold', active ? 'text-ink' : 'text-muted')} aria-current={active ? 'step' : undefined}>{step}</span>
                  </div>
                  <span className={cn('mt-2 block h-0.5', active || complete ? 'bg-[#1c5d9c]' : 'bg-line')} aria-hidden="true" />
                </li>
              );
            })}
          </ol>
        </nav>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {currentStep === 1 && <SourceStep sourceType={sourceType} onSelect={setSourceType} />}
          {currentStep === 2 && <MappingStep editing={mappingEditing} onToggleEditing={() => setMappingEditing((editing) => !editing)} />}
          {currentStep === 3 && <ValidationStep showWarnings={showWarnings} onToggleWarnings={() => setShowWarnings((visible) => !visible)} />}
          {currentStep === 4 && <ConfirmationStep datasetName={datasetName} onNameChange={setDatasetName} />}
        </div>

        <footer className="flex items-center justify-between gap-3 border-t border-line bg-white px-6 py-4">
          <button type="button" onClick={() => currentStep === 1 ? onClose() : setCurrentStep((step) => step - 1)} className="secondary-button">
            {currentStep === 1 ? 'Hủy' : <><ChevronLeft size={15} aria-hidden="true" /> Quay lại</>}
          </button>
          <button type="button" onClick={handleNext} className="primary-button">
            {currentStep === steps.length ? 'Tạo bộ dữ liệu' : <>Tiếp tục <ArrowRight size={15} aria-hidden="true" /></>}
          </button>
        </footer>
      </aside>
    </div>
  );
}

function SourceStep({ sourceType, onSelect }: { sourceType: SourceType; onSelect: (source: SourceType) => void }) {
  return (
    <section aria-labelledby="source-step-heading">
      <StepHeading title="Chọn loại nguồn dữ liệu" helper="Chọn nguồn bạn muốn đưa vào bộ dữ liệu. Cấu hình kết nối chi tiết sẽ được bổ sung sau." />
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {sourceOptions.map(({ label, description, icon: Icon }) => {
          const selected = label === sourceType;
          return (
            <button key={label} type="button" aria-pressed={selected} onClick={() => onSelect(label)} className={cn('flex min-h-[112px] items-start gap-3 border bg-white p-4 text-left transition hover:border-[#8db6d9] hover:bg-[#f7fafc]', selected ? 'border-[#1c5d9c] bg-[#f5f8fb]' : 'border-line')}>
              <span className={cn('grid h-9 w-9 shrink-0 place-items-center border', selected ? 'border-[#8db6d9] bg-white text-[#1c5d9c]' : 'border-line text-muted')}><Icon size={18} aria-hidden="true" /></span>
              <span><span className="block text-sm font-semibold text-ink">{label}</span><span className="mt-1 block text-xs leading-5 text-muted">{description}</span></span>
            </button>
          );
        })}
      </div>
      <div className="mt-6 border border-[#d7e5ef] bg-[#f5f8fb] px-4 py-3 text-xs leading-5 text-[#41637e]">
        <p className="font-semibold text-ink">Nguồn được xử lý theo cùng một nguyên tắc</p>
        <p className="mt-1">Hệ thống nhận diện dữ liệu, kiểm tra chất lượng rồi tạo bộ dữ liệu cho phân tích.</p>
      </div>
    </section>
  );
}

function MappingStep({ editing, onToggleEditing }: { editing: boolean; onToggleEditing: () => void }) {
  const rows = [
    { source: 'Company', label: 'Doanh nghiệp', valid: true },
    { source: 'Quarter', label: 'Kỳ dữ liệu', valid: true },
    { source: 'NPL Ratio', label: 'NPL', valid: true },
    { source: 'ROE (%)', label: 'ROE', valid: true },
    { source: 'Unnamed_12', label: 'Chưa xác định', valid: false }
  ];

  return (
    <section aria-labelledby="mapping-step-heading">
      <StepHeading title="Nhận diện dữ liệu" helper="Hệ thống đã nhận diện cấu trúc ban đầu của nguồn. Kiểm tra lại trước khi tiếp tục." />
      <div className="mt-5 overflow-hidden border border-line bg-white">
        {rows.map((row) => (
          <div key={row.source} className="grid grid-cols-[minmax(0,1fr)_28px_minmax(0,1fr)] items-center gap-3 border-b border-line px-4 py-3 last:border-b-0">
            <span className="truncate text-sm text-ink">{row.source}</span>
            <ArrowRight size={15} className="text-slate-400" aria-hidden="true" />
            {row.valid ? <span className="flex items-center gap-2 text-sm font-semibold text-ink"><CheckCircle2 size={16} className="text-ready" aria-hidden="true" />{row.label}</span> : editing ? <select aria-label={`Điều chỉnh mapping cho ${row.source}`} defaultValue="unknown" className="field-control py-1.5 text-xs"><option value="unknown">Chưa xác định</option><option value="metric">Chỉ tiêu</option><option value="ignore">Bỏ qua</option></select> : <span className="flex items-center gap-2 text-sm font-semibold text-warning"><AlertTriangle size={16} aria-hidden="true" />{row.label}</span>}
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-xs leading-5 text-muted">Tên cột được hiển thị bằng thuật ngữ nghiệp vụ để dễ kiểm tra.</p>
        <button type="button" onClick={onToggleEditing} className="secondary-button shrink-0">{editing ? 'Lưu mapping' : 'Điều chỉnh mapping'}</button>
      </div>
    </section>
  );
}

function ValidationStep({ showWarnings, onToggleWarnings }: { showWarnings: boolean; onToggleWarnings: () => void }) {
  return (
    <section aria-labelledby="validation-step-heading">
      <StepHeading title="Kiểm tra dữ liệu" helper="Các giá trị thiếu được giữ nguyên để người phân tích biết giới hạn của dữ liệu." />
      <div className="mt-5 border border-line bg-white">
        <div className="border-b border-line px-4 py-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Tổng quan kiểm tra</p><p className="mt-2 font-display text-3xl font-semibold text-ink">80 <span className="font-sans text-sm font-medium text-muted">quan sát</span></p></div>
        <div className="divide-y divide-line">
          <ValidationRow icon={<CheckCircle2 size={16} />} tone="ready" text="76 hợp lệ" />
          <ValidationRow icon={<AlertTriangle size={16} />} tone="warning" text="4 giá trị thiếu" />
          <ValidationRow icon={<CheckCircle2 size={16} />} tone="ready" text="Không có dữ liệu trùng" />
          <ValidationRow icon={<CheckCircle2 size={16} />} tone="ready" text="Đơn vị dữ liệu hợp lệ" />
        </div>
      </div>
      <button type="button" onClick={onToggleWarnings} className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-[#1c5d9c] underline decoration-[#a8c5df] underline-offset-4">{showWarnings ? 'Ẩn cảnh báo' : 'Tìm hiểu 4 cảnh báo'}</button>
      {showWarnings && <div className="mt-3 border border-[#ead6b5] bg-[#fffaf1] px-4 py-3 text-xs leading-5 text-[#6e5225]" role="status"><p className="font-semibold">4 giá trị thiếu chưa được điền tự động.</p><p className="mt-1">Bạn có thể tiếp tục tạo bộ dữ liệu và công bố giới hạn này trong báo cáo.</p></div>}
    </section>
  );
}

function ConfirmationStep({ datasetName, onNameChange }: { datasetName: string; onNameChange: (name: string) => void }) {
  return (
    <section aria-labelledby="confirmation-step-heading">
      <StepHeading title="Xác nhận bộ dữ liệu" helper="Kiểm tra phạm vi được nhận diện trước khi tạo bộ dữ liệu." />
      <label htmlFor="dataset-name" className="mt-5 block text-sm font-semibold text-ink">Tên bộ dữ liệu</label>
      <input id="dataset-name" value={datasetName} onChange={(event) => onNameChange(event.target.value)} className="field-control mt-2" />
      <div className="mt-6 divide-y divide-line border-y border-line bg-white">
        <CoverageRow label="Doanh nghiệp" value="ACB · TCB · MBB · VCB · VPB" />
        <CoverageRow label="Thời gian" value="Q1 · Q2 · Q3 · Q4 2024" />
        <CoverageRow label="Chỉ tiêu" value="NPL · Coverage · ROA · ROE" />
      </div>
    </section>
  );
}

function StepHeading({ title, helper }: { title: string; helper: string }) {
  return <div><h3 className="text-lg font-semibold tracking-[-0.015em] text-ink">{title}</h3><p className="mt-1 max-w-[58ch] text-xs leading-5 text-muted">{helper}</p></div>;
}

function ValidationRow({ icon, tone, text }: { icon: ReactNode; tone: 'ready' | 'warning'; text: string }) {
  return <div className="flex items-center gap-2 px-4 py-3 text-sm"><span className={tone === 'ready' ? 'text-ready' : 'text-warning'} aria-hidden="true">{icon}</span><span className="text-ink">{text}</span></div>;
}

function CoverageRow({ label, value }: { label: string; value: string }) {
  return <div className="grid gap-1 px-4 py-3 sm:grid-cols-[120px_1fr] sm:gap-4"><span className="text-xs font-semibold text-muted">{label}</span><span className="text-sm text-ink">{value}</span></div>;
}
