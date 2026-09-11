import { FileText, WandSparkles } from 'lucide-react';
import type { Control, FieldErrors, UseFormRegister } from 'react-hook-form';
import { useWatch } from 'react-hook-form';
import type { AnalysisFormValues } from '../schema';

interface AnalysisIntentSectionProps {
  control: Control<AnalysisFormValues>;
  errors: FieldErrors<AnalysisFormValues>;
  register: UseFormRegister<AnalysisFormValues>;
  canSuggest: boolean;
  objectiveWasEdited: boolean;
  scopeChangedNotice: boolean;
  possibleMismatch: boolean;
  onSuggest: () => void;
  onUpdateSuggestion: () => void;
  onKeepObjective: () => void;
}

export function AnalysisIntentSection({
  control,
  errors,
  register,
  canSuggest,
  objectiveWasEdited,
  scopeChangedNotice,
  possibleMismatch,
  onSuggest,
  onUpdateSuggestion,
  onKeepObjective
}: AnalysisIntentSectionProps) {
  const objective = useWatch({ control, name: 'objective' }) ?? '';

  return (
    <section className="surface-section" aria-labelledby="intent-heading">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <label htmlFor="analysis-objective" className="section-title block">Mục tiêu phân tích <span className="text-blocked">*</span></label>
          <p className="section-helper">Mô tả câu hỏi hoặc mục tiêu bạn muốn phân tích.</p>
        </div>
        <button
          type="button"
          onClick={onSuggest}
          disabled={!canSuggest}
          className="secondary-button"
          title={!canSuggest ? 'Chọn đối tượng, kỳ và chủ đề trước' : undefined}
        >
          <WandSparkles size={16} aria-hidden="true" />
          Dùng mục tiêu gợi ý
        </button>
      </div>

      <div className="relative mt-4">
        <FileText size={17} className="pointer-events-none absolute left-3 top-3 text-muted" aria-hidden="true" />
        <textarea
          {...register('objective')}
          id="analysis-objective"
          maxLength={500}
          aria-describedby="objective-help objective-error"
          aria-invalid={Boolean(errors.objective)}
          className="field-control min-h-[104px] resize-y pl-10 pr-14 leading-6"
          placeholder="Ví dụ: So sánh xu hướng NPL và Coverage của ACB, TCB và MBB qua Q1–Q4/2024."
        />
        <span className="absolute bottom-2 right-3 text-xs tabular-nums text-muted">{objective.length}/500</span>
      </div>
      <p id="objective-help" className="mt-2 text-xs text-muted">Mục tiêu là bắt buộc và tối đa 500 ký tự. Lựa chọn có cấu trúc là ranh giới thực thi của yêu cầu.</p>

      {errors.objective && <p id="objective-error" className="field-error" role="alert">{errors.objective.message}</p>}

      {scopeChangedNotice && (
        <div className="notice notice-warning mt-4" role="status">
          <div>
            <p className="font-semibold">Phạm vi đã thay đổi. Mục tiêu hiện tại có thể không còn phản ánh lựa chọn mới.</p>
            {objectiveWasEdited && <p className="mt-1 text-xs">Mục tiêu đã được chỉnh sửa; hệ thống sẽ không ghi đè nội dung này.</p>}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" onClick={onUpdateSuggestion} className="notice-action">Cập nhật mục tiêu gợi ý</button>
            <button type="button" onClick={onKeepObjective} className="notice-link">Giữ mục tiêu hiện tại</button>
          </div>
        </div>
      )}

      {possibleMismatch && (
        <div className="notice notice-warning mt-4" role="status">
          <p className="font-semibold">Hệ thống phát hiện yêu cầu có thể vượt ngoài phạm vi đã chọn.</p>
          <p className="mt-1 text-xs">Vui lòng kiểm tra lại mục tiêu và phạm vi có cấu trúc. Phạm vi này vẫn là ranh giới thực thi.</p>
        </div>
      )}
    </section>
  );
}
