import { Scale, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { formatMetric } from '@/shared/lib/formatting';
import type { CompanyInsight, SectorBenchmark } from '../model/types';

interface SectorBenchmarkMatrixProps {
  sectorBenchmark?: SectorBenchmark | null;
  targetTicker: string;
  peerTickers: string[];
  companyInsights: CompanyInsight[];
}

interface BenchmarkMetricRow {
  key: keyof Omit<SectorBenchmark, 'sector'>;
  insightKey: keyof Omit<CompanyInsight, 'ticker' | 'assessment'>;
  code: string;
  label: string;
  description: string;
  unit: '%' | 'bps';
  higherIsBetter: boolean;
}

const BENCHMARK_METRICS: BenchmarkMetricRow[] = [
  {
    key: 'peer_median_roe',
    insightKey: 'roe',
    code: 'ROE',
    label: 'Tỷ suất sinh lời trên vốn CSH',
    description: 'Đo lường hiệu quả sinh lời tổng thể trên vốn cổ đông',
    unit: '%',
    higherIsBetter: true
  },
  {
    key: 'peer_median_nim',
    insightKey: 'nim',
    code: 'NIM',
    label: 'Biên lãi thuần',
    description: 'Chênh lệch giữa thu nhập lãi thuần và tài sản sinh lời bình quân',
    unit: '%',
    higherIsBetter: true
  },
  {
    key: 'peer_median_npl',
    insightKey: 'npl',
    code: 'NPL',
    label: 'Tỷ lệ nợ xấu (Nhóm 3-5)',
    description: 'Đánh giá rủi ro tín dụng và chất lượng danh mục cho vay',
    unit: '%',
    higherIsBetter: false
  },
  {
    key: 'peer_median_cir',
    insightKey: 'cir',
    code: 'CIR',
    label: 'Tỷ lệ chi phí trên thu nhập',
    description: 'Hiệu quả kiểm soát chi phí vận hành so với tổng thu nhập',
    unit: '%',
    higherIsBetter: false
  },
  {
    key: 'peer_median_casa',
    insightKey: 'casa',
    code: 'CASA',
    label: 'Tỷ lệ tiền gửi không kỳ hạn',
    description: 'Tỷ trọng tiền gửi giá rẻ hỗ trợ giảm thiểu giá vốn huy động (COF)',
    unit: '%',
    higherIsBetter: true
  },
  {
    key: 'peer_median_car',
    insightKey: 'car',
    code: 'CAR',
    label: 'Hệ số an toàn vốn',
    description: 'Đệm vốn tự có bảo vệ trước rủi ro tín dụng, thị trường và hoạt động',
    unit: '%',
    higherIsBetter: true
  },
  {
    key: 'peer_median_ldr',
    insightKey: 'ldr',
    code: 'LDR',
    label: 'Tỷ lệ cho vay trên huy động vốn',
    description: 'Thước đo mức độ sử dụng nguồn vốn và an toàn thanh khoản',
    unit: '%',
    higherIsBetter: false
  }
];

export function SectorBenchmarkMatrix({
  sectorBenchmark,
  targetTicker,
  peerTickers,
  companyInsights
}: SectorBenchmarkMatrixProps) {
  if (!sectorBenchmark) {
    return null;
  }

  const targetInsight = companyInsights.find((c) => c.ticker === targetTicker);
  const peerInsight = companyInsights.find((c) => peerTickers.includes(c.ticker));

  return (
    <section className="border border-line bg-card rounded-lg p-5 space-y-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-3">
        <div className="flex items-center gap-2">
          <Scale className="size-4 text-ink-secondary" aria-hidden="true" />
          <h2 className="text-sm font-bold tracking-tight text-ink">
            Đối chuẩn trung vị ngành ngân hàng
          </h2>
        </div>

        <div className="text-xs text-ink-secondary font-mono">
          <span>Đối chuẩn: </span>
          <span className="font-semibold text-ink">{sectorBenchmark.sector}</span>
        </div>
      </div>

      <p className="text-xs text-ink-secondary leading-relaxed">
        So sánh định lượng giữa ngân hàng mục tiêu ({targetTicker}), nhóm đối chuẩn ({peerTickers.join(', ') || 'TCB'}) và trung vị ngành niêm yết năm 2024.
      </p>

      {/* Table */}
      <div className="border border-line rounded-md overflow-x-auto bg-surface-primary">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-line bg-surface-secondary text-[11px] font-mono font-bold uppercase tracking-wider text-ink-secondary">
              <th className="py-2.5 px-3">Chỉ tiêu</th>
              <th className="py-2.5 px-3 hidden md:table-cell">Mô tả nghiệp vụ</th>
              <th className="py-2.5 px-3 text-right bg-amber-soft/20 text-ink">
                {targetTicker} (Mục tiêu)
              </th>
              {peerInsight && (
                <th className="py-2.5 px-3 text-right">
                  {peerInsight.ticker} (Đối thủ)
                </th>
              )}
              <th className="py-2.5 px-3 text-right font-bold text-ink">
                Trung vị ngành
              </th>
              <th className="py-2.5 px-3 text-right">
                Độ lệch {targetTicker} vs Ngành
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {BENCHMARK_METRICS.map((m) => {
              const medianVal = sectorBenchmark[m.key];
              const targetVal = targetInsight ? targetInsight[m.insightKey] : undefined;
              const peerVal = peerInsight ? peerInsight[m.insightKey] : undefined;

              const hasTarget = targetVal !== null && targetVal !== undefined && !isNaN(Number(targetVal));
              const hasMedian = medianVal !== null && medianVal !== undefined && !isNaN(Number(medianVal));

              const delta =
                hasTarget && hasMedian
                  ? Number(targetVal) - Number(medianVal)
                  : undefined;
              const isFavorable =
                delta !== undefined
                  ? m.higherIsBetter
                    ? delta > 0
                    : delta < 0
                  : false;

              return (
                <tr key={m.code} className="hover:bg-surface-hover/60 transition-colors">
                  <td className="py-2.5 px-3">
                    <div className="font-mono font-bold text-ink">{m.code}</div>
                    <div className="text-[11px] text-ink-secondary md:hidden">{m.label}</div>
                  </td>
                  <td className="py-2.5 px-3 hidden md:table-cell text-ink-secondary">
                    <span className="font-medium text-ink">{m.label}</span>
                    <span className="text-ink-tertiary"> — {m.description}</span>
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono font-bold text-ink bg-amber-soft/10">
                    {targetInsight ? formatMetric(targetVal, 2) : '—'}
                  </td>
                  {peerInsight && (
                    <td className="py-2.5 px-3 text-right font-mono text-ink-secondary">
                      {formatMetric(peerVal, 2)}
                    </td>
                  )}
                  <td className="py-2.5 px-3 text-right font-mono font-semibold text-ink">
                    {formatMetric(medianVal, 2)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono">
                    {delta !== undefined ? (
                      <span
                        className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[11px] font-bold ${
                          isFavorable
                            ? 'bg-[#e8f5ee] text-[#1b4332]'
                            : Math.abs(delta) < 0.05
                            ? 'bg-surface-secondary text-ink-secondary'
                            : 'bg-amber-soft/40 text-amber-border'
                        }`}
                      >
                        {delta > 0 ? (
                          <ArrowUpRight className="size-3" aria-hidden="true" />
                        ) : delta < 0 ? (
                          <ArrowDownRight className="size-3" aria-hidden="true" />
                        ) : (
                          <Minus className="size-3" aria-hidden="true" />
                        )}
                        <span>
                          {delta > 0 ? '+' : ''}
                          {formatMetric(delta, 2)}
                        </span>
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
