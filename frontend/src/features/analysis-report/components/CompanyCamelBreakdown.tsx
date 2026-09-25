import { Building2 } from 'lucide-react';
import { formatMetric } from '@/shared/lib/formatting';
import type { CompanyInsight } from '../model/types';

interface CompanyCamelBreakdownProps {
  companyInsights: CompanyInsight[];
  targetTicker: string;
}

const METRICS: Array<{ key: keyof Omit<CompanyInsight, 'ticker' | 'assessment'>; label: string }> = [
  { key: 'npl', label: 'NPL' },
  { key: 'roe', label: 'ROE' },
  { key: 'nim', label: 'NIM' },
  { key: 'cir', label: 'CIR' },
  { key: 'casa', label: 'CASA' },
  { key: 'car', label: 'CAR' },
  { key: 'ldr', label: 'LDR' }
];

export function CompanyCamelBreakdown({ companyInsights, targetTicker }: CompanyCamelBreakdownProps) {
  const companies = [...companyInsights].sort((left, right) =>
    Number(right.ticker === targetTicker) - Number(left.ticker === targetTicker)
  );
  const availableMetrics = METRICS.filter(({ key }) =>
    companies.some((company) => typeof company[key] === 'number' && Number.isFinite(company[key]))
  );

  return (
    <section className="rounded-md border border-line bg-card p-5" aria-labelledby="company-metrics-heading">
      <div className="flex items-center gap-2 border-b border-line pb-3">
        <Building2 className="size-4 text-ink-secondary" aria-hidden="true" />
        <h2 id="company-metrics-heading" className="text-sm font-bold text-ink">Chỉ tiêu doanh nghiệp trong báo cáo</h2>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-ink-secondary">
        Chỉ hiển thị giá trị do API trả về. Luận điểm, trạng thái và bằng chứng được hiển thị theo phản hồi API.
      </p>
      {availableMetrics.length === 0 ? (
        <p className="mt-4 rounded-md border border-line bg-surface-secondary p-3 text-sm text-ink-secondary">
          Chưa có chỉ tiêu doanh nghiệp nào được công bố trong báo cáo này.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-md border border-line">
          <table className="w-full border-collapse text-left text-xs">
            <thead className="bg-surface-secondary text-ink-secondary">
              <tr>
                <th scope="col" className="px-3 py-2 font-semibold">Chỉ tiêu</th>
                {companies.map((company) => (
                  <th scope="col" key={company.ticker} className="px-3 py-2 text-right font-semibold">
                    {company.ticker}{company.ticker === targetTicker ? ' · Mục tiêu' : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {availableMetrics.map(({ key, label }) => (
                <tr key={key} className="border-t border-line">
                  <th scope="row" className="px-3 py-2 font-semibold text-ink">{label}</th>
                  {companies.map((company) => (
                    <td key={company.ticker} className="px-3 py-2 text-right font-mono text-ink">
                      {typeof company[key] === 'number' && Number.isFinite(company[key])
                        ? formatMetric(company[key], 2)
                        : '— (thiếu)'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
