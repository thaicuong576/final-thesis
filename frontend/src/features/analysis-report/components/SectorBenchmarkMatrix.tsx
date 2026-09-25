import { Scale } from 'lucide-react';
import { formatMetric } from '@/shared/lib/formatting';
import type { SectorBenchmark } from '../model/types';

interface SectorBenchmarkMatrixProps {
  sectorBenchmark: SectorBenchmark;
  period?: string;
}

const BENCHMARK_METRICS: Array<{
  key: keyof Omit<SectorBenchmark, 'sector'>;
  label: string;
}> = [
  { key: 'peer_median_roe', label: 'ROE' },
  { key: 'peer_median_nim', label: 'NIM' },
  { key: 'peer_median_npl', label: 'NPL' },
  { key: 'peer_median_cir', label: 'CIR' },
  { key: 'peer_median_casa', label: 'CASA' },
  { key: 'peer_median_car', label: 'CAR' },
  { key: 'peer_median_ldr', label: 'LDR' }
];

export function SectorBenchmarkMatrix({ sectorBenchmark, period }: SectorBenchmarkMatrixProps) {
  const rows = BENCHMARK_METRICS.filter(({ key }) => sectorBenchmark[key] !== undefined);

  return (
    <section className="rounded-md border border-line bg-card p-5" aria-labelledby="sector-benchmark-heading">
      <div className="flex flex-col gap-2 border-b border-line pb-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Scale className="size-4 text-ink-secondary" aria-hidden="true" />
          <h2 id="sector-benchmark-heading" className="text-sm font-bold text-ink">
            Đối chuẩn do API trả về
          </h2>
        </div>
        <div className="text-xs font-mono text-ink-secondary">
          {sectorBenchmark.sector}{period ? ` · ${period}` : ''}
        </div>
      </div>

      <p className="mt-3 text-xs leading-relaxed text-ink-secondary">
        Bảng chỉ hiển thị trung vị có trong phản hồi API. Không có giá trị thì được giữ là thiếu dữ liệu.
      </p>

      {rows.length === 0 ? (
        <p className="mt-4 rounded-md border border-line bg-surface-secondary p-3 text-sm text-ink-secondary">
          API không trả về giá trị đối chuẩn nào.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-md border border-line">
          <table className="w-full border-collapse text-left text-xs">
            <thead className="bg-surface-secondary text-ink-secondary">
              <tr>
                <th scope="col" className="px-3 py-2 font-semibold">Chỉ tiêu</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Trung vị API công bố</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ key, label }) => {
                const value = sectorBenchmark[key];
                return (
                  <tr key={key} className="border-t border-line">
                    <th scope="row" className="px-3 py-2 font-semibold text-ink">{label}</th>
                    <td className="px-3 py-2 text-right font-mono text-ink">
                      {typeof value === 'number' && Number.isFinite(value)
                        ? formatMetric(value, 2)
                        : '— (thiếu)'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
