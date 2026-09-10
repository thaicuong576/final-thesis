import type { FieldErrors, UseFormSetValue, UseFormWatch } from 'react-hook-form';
import type { AnalysisCapabilities } from '../../../entities/capability/model/types';
import type { AnalysisFormValues } from '../schema';
import { cn } from '../../../shared/lib/cn';

interface ScopeSelectorsProps {
  capabilities: AnalysisCapabilities;
  errors: FieldErrors<AnalysisFormValues>;
  setValue: UseFormSetValue<AnalysisFormValues>;
  watch: UseFormWatch<AnalysisFormValues>;
}

export function ScopeSelectors({ capabilities, errors, setValue, watch }: ScopeSelectorsProps) {
  const selectedTargets = watch('analysisTargetIds') ?? [];
  const selectedPeriods = watch('periodIds') ?? [];

  function toggleValue(field: 'analysisTargetIds' | 'periodIds', id: string) {
    const current = watch(field) ?? [];
    const next = current.includes(id) ? current.filter((value) => value !== id) : [...current, id];
    setValue(field, next, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
  }

  return (
    <section className="surface-section" aria-labelledby="scope-heading">
      <div className="mb-6">
        <h2 id="scope-heading" className="section-title">Phạm vi phân tích</h2>
        <p className="section-helper">Structured scope xác định chính xác dữ liệu được đưa vào yêu cầu.</p>
      </div>

      <div className="space-y-7">
        <div>
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <h3 className="field-label">Đối tượng phân tích <span className="text-blocked">*</span></h3>
              <p className="section-helper">Chọn các ngân hàng cần phân tích chính.</p>
            </div>
            <span className="text-xs font-medium text-muted">{selectedTargets.length}/5 đã chọn</span>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            {capabilities.entities.map((entity) => (
              <CheckOption key={entity.id} id={`target-${entity.id}`} label={entity.ticker} checked={selectedTargets.includes(entity.id)} onChange={() => toggleValue('analysisTargetIds', entity.id)} />
            ))}
          </div>
          {errors.analysisTargetIds && <p className="field-error">{errors.analysisTargetIds.message}</p>}
        </div>

        <div>
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <h3 className="field-label">Kỳ tài chính <span className="text-blocked">*</span></h3>
              <p className="section-helper">Chọn một hoặc nhiều kỳ được hỗ trợ.</p>
            </div>
            <span className="text-xs font-medium text-muted">{selectedPeriods.length}/4 đã chọn</span>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {capabilities.periods.map((period) => (
              <CheckOption key={period.id} id={`period-${period.id}`} label={period.label} checked={selectedPeriods.includes(period.id)} onChange={() => toggleValue('periodIds', period.id)} />
            ))}
          </div>
          {errors.periodIds && <p className="field-error">{errors.periodIds.message}</p>}
        </div>
      </div>
    </section>
  );
}

function CheckOption({ id, label, checked, onChange }: { id: string; label: string; checked: boolean; onChange: () => void }) {
  return (
    <label htmlFor={id} className={cn('check-option', checked && 'check-option-selected')}>
      <input id={id} type="checkbox" checked={checked} onChange={onChange} />
      <span>{label}</span>
    </label>
  );
}
