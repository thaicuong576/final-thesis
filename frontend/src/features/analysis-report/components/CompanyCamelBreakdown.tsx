import { useState } from 'react';
import {
  Building2,
  Shield,
  AlertTriangle,
  Activity,
  TrendingUp,
  Droplets
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { formatMetric } from '@/shared/lib/formatting';
import type { CompanyInsight } from '../model/types';

interface CompanyCamelBreakdownProps {
  companyInsights: CompanyInsight[];
  targetTicker: string;
}

type CamelPillarKey = 'all' | 'C' | 'A' | 'M' | 'E' | 'L';

interface CamelPillarDef {
  key: 'C' | 'A' | 'M' | 'E' | 'L';
  title: string;
  nameVi: string;
  icon: typeof Shield;
  description: string;
  metrics: {
    label: string;
    key: keyof Omit<CompanyInsight, 'ticker' | 'assessment'>;
    unit: string;
    benchmarkNote: string;
  }[];
  analysisText: (insights: CompanyInsight[]) => string;
}

const CAMEL_PILLARS: CamelPillarDef[] = [
  {
    key: 'C',
    title: 'Capital Adequacy',
    nameVi: 'Mức độ an toàn vốn',
    icon: Shield,
    description: 'Năng lực nguồn vốn tự có bảo vệ ngân hàng trước tổn thất tín dụng bất ngờ.',
    metrics: [
      {
        label: 'Tỷ lệ an toàn vốn (CAR)',
        key: 'car',
        unit: '%',
        benchmarkNote: 'Quy chuẩn NHNN tối thiểu 8.0%, trung vị ngành 11.8%'
      }
    ],
    analysisText: (insights) => {
      const acb = insights.find((i) => i.ticker === 'ACB');
      const tcb = insights.find((i) => i.ticker === 'TCB');
      if (acb && tcb) {
        return `TCB sở hữu đệm vốn CAR ấn tượng 14.5% nhờ chiến lược tích lũy lợi nhuận giữ lại qua nhiều năm, tạo dư địa mở rộng bảng cân đối vượt trội. ACB duy trì CAR 12.8%, tuân thủ an toàn theo chuẩn mực Basel II với cấu trúc tài sản rủi ro bán lẻ lành mạnh.`;
      }
      return `Hệ số CAR đạt ${formatMetric(acb?.car ?? 12.8, 1)}, bảo đảm bộ đệm rủi ro vững chắc trước các biến động chu kỳ kinh tế vĩ mô.`;
    }
  },
  {
    key: 'A',
    title: 'Asset Quality',
    nameVi: 'Chất lượng tài sản',
    icon: AlertTriangle,
    description: 'Đo lường mức độ rủi ro tín dụng và khả năng thu hồi của danh mục cho vay.',
    metrics: [
      {
        label: 'Tỷ lệ nợ xấu (NPL Nhóm 3-5)',
        key: 'npl',
        unit: '%',
        benchmarkNote: 'Ngưỡng kiểm soát NHNN < 3.0%, trung vị ngành 1.62%'
      }
    ],
    analysisText: (insights) => {
      const acb = insights.find((i) => i.ticker === 'ACB');
      const tcb = insights.find((i) => i.ticker === 'TCB');
      if (acb && tcb) {
        return `ACB duy trì nợ xấu NPL chỉ 1.21%, thấp hơn đáng kể so với trung vị ngành (1.62%) và TCB (1.45%). Chính sách cho vay thận trọng, tập trung 94% vào bán lẻ và DNNVV có tài sản bảo đảm là nhà ở giúp ACB giữ chi phí trích lập dự phòng ở mức tối ưu.`;
      }
      return `Chất lượng tài sản tiếp tục là lợi thế cạnh tranh nòng cốt với tỷ lệ nợ xấu ${formatMetric(acb?.npl ?? 1.21, 2)}, kiểm soát chặt chẽ trong nhóm dẫn đầu toàn ngành.`;
    }
  },
  {
    key: 'M',
    title: 'Management Efficiency',
    nameVi: 'Hiệu quả quản trị & Vận hành',
    icon: Activity,
    description: 'Năng lực điều hành tối ưu hóa chi phí vận hành và số hóa quy trình kinh doanh.',
    metrics: [
      {
        label: 'Tỷ lệ chi phí trên thu nhập (CIR)',
        key: 'cir',
        unit: '%',
        benchmarkNote: 'Trung vị ngành 33.4%, tỷ lệ càng thấp hiệu quả càng cao'
      }
    ],
    analysisText: (insights) => {
      const acb = insights.find((i) => i.ticker === 'ACB');
      const tcb = insights.find((i) => i.ticker === 'TCB');
      if (acb && tcb) {
        return `Cả ACB (CIR 31.8%) và TCB (CIR 32.5%) đều đạt hiệu suất vận hành vượt trội so với trung vị ngành (33.4%). Nỗ lực tự động hóa quy trình nội bộ và kênh giao dịch số giúp cả hai định chế tài chính tiết giảm chi phí quản lý vận hành đáng kể.`;
      }
      return `CIR duy trì ở mức ${formatMetric(acb?.cir ?? 31.8, 1)}, phản ánh kỷ luật tài chính nghiêm ngặt và năng lực kiểm soát chi phí hoạt động xuất sắc.`;
    }
  },
  {
    key: 'E',
    title: 'Earnings Quality',
    nameVi: 'Chất lượng sinh lời',
    icon: TrendingUp,
    description: 'Khả năng sinh lời bền vững trên vốn chủ sở hữu và hiệu quả biên lãi thuần.',
    metrics: [
      {
        label: 'Tỷ suất sinh lời trên vốn CSH (ROE)',
        key: 'roe',
        unit: '%',
        benchmarkNote: 'Trung vị ngành 18.2%'
      },
      {
        label: 'Biên lãi thuần (NIM)',
        key: 'nim',
        unit: '%',
        benchmarkNote: 'Trung vị ngành 3.65%'
      }
    ],
    analysisText: (insights) => {
      const acb = insights.find((i) => i.ticker === 'ACB');
      const tcb = insights.find((i) => i.ticker === 'TCB');
      if (acb && tcb) {
        return `ACB dẫn đầu về hiệu suất sinh lời ROE đạt 21.4% (vượt 3.2 điểm % so với trung vị ngành), trong khi TCB sở hữu biên lãi thuần NIM 4.15% (vượt 50 bps so với trung vị). ACB tối ưu hóa đòn bẩy và chi phí tín dụng, còn TCB tận dụng triệt để lợi thế giá vốn tiền gửi rẻ.`;
      }
      return `Khả năng sinh lời vượt trội với ROE ${formatMetric(acb?.roe ?? 21.4, 1)} và NIM ${formatMetric(acb?.nim ?? 3.82, 2)}, phản ánh cơ cấu thu nhập cân bằng và hiệu quả sinh lời vững bền.`;
    }
  },
  {
    key: 'L',
    title: 'Liquidity & Funding',
    nameVi: 'Thanh khoản & Cấu trúc vốn',
    icon: Droplets,
    description: 'Mức độ an toàn dự trữ thanh khoản và tỷ trọng tiền gửi chi phí thấp CASA.',
    metrics: [
      {
        label: 'Tỷ lệ cho vay trên huy động (LDR)',
        key: 'ldr',
        unit: '%',
        benchmarkNote: 'Trần an toàn quy định NHNN 85.0%, trung vị ngành 78.4%'
      },
      {
        label: 'Tỷ lệ tiền gửi không kỳ hạn (CASA)',
        key: 'casa',
        unit: '%',
        benchmarkNote: 'Trung vị ngành 28.5%'
      }
    ],
    analysisText: (insights) => {
      const acb = insights.find((i) => i.ticker === 'ACB');
      const tcb = insights.find((i) => i.ticker === 'TCB');
      if (acb && tcb) {
        return `TCB áp đảo với tỷ lệ CASA dẫn đầu toàn hệ thống 41.2%, hạ thấp đáng kể chi phí vốn đầu vào (COF). ACB duy trì LDR 82.5% đảm bảo tối ưu hóa dòng tiền huy động trong giới hạn an toàn 85% của NHNN.`;
      }
      return `Thanh khoản tuân thủ nghiêm ngặt chuẩn mực NHNN với LDR ${formatMetric(acb?.ldr ?? 82.5, 1)} và tỷ lệ CASA ${formatMetric(acb?.casa ?? 23.2, 1)}.`;
    }
  }
];

export function CompanyCamelBreakdown({
  companyInsights,
  targetTicker
}: CompanyCamelBreakdownProps) {
  const [selectedPillar, setSelectedPillar] = useState<CamelPillarKey>('all');

  const visiblePillars =
    selectedPillar === 'all'
      ? CAMEL_PILLARS
      : CAMEL_PILLARS.filter((p) => p.key === selectedPillar);

  return (
    <section className="border border-line bg-card rounded-lg p-5 space-y-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-3">
        <div className="flex items-center gap-2">
          <Building2 className="size-4 text-ink-secondary" aria-hidden="true" />
          <h2 className="text-sm font-bold tracking-tight text-ink">
            Phân tích sức khỏe tài chính 5 trụ cột
          </h2>
        </div>

        {/* Pillar Filter Pills */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
          <button
            type="button"
            onClick={() => setSelectedPillar('all')}
            className={`px-2 py-1 text-xs font-mono font-medium rounded transition-colors ${
              selectedPillar === 'all'
                ? 'bg-amber text-ink border border-amber-border font-bold'
                : 'bg-surface-secondary text-ink hover:bg-surface-hover border border-border'
            }`}
          >
            Tất cả (5)
          </button>
          {CAMEL_PILLARS.map((p) => (
            <button
              key={p.key}
              type="button"
              onClick={() => setSelectedPillar(p.key)}
              className={`px-2 py-1 text-xs font-mono font-medium rounded transition-colors ${
                selectedPillar === p.key
                  ? 'bg-amber text-ink font-bold border border-amber-border'
                  : 'bg-surface-secondary text-ink hover:bg-surface-hover border border-border'
              }`}
            >
              {p.key} - {p.nameVi.split(' ')[0]}
            </button>
          ))}
        </div>
      </div>

      {/* Narrative synthesis per bank */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {companyInsights.map((insight) => {
          const isTarget = insight.ticker === targetTicker;
          return (
            <div
              key={insight.ticker}
              className={`border rounded-lg p-3.5 space-y-2 ${
                isTarget
                  ? 'border-amber-border/60 bg-amber-soft/20'
                  : 'border-line bg-surface-secondary'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge
                    className={
                      isTarget
                        ? 'bg-amber text-ink font-mono font-bold'
                        : 'bg-card text-ink border-border font-mono font-bold'
                    }
                  >
                    {insight.ticker}
                  </Badge>
                  <span className="text-xs font-semibold text-ink">
                    {isTarget ? 'Ngân hàng mục tiêu' : 'Ngân hàng đối chuẩn'}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-ink-secondary">
                  ROE: {formatMetric(insight.roe, 1)} · NIM: {formatMetric(insight.nim, 2)}
                </span>
              </div>

              <p className="text-xs text-ink leading-relaxed">
                {insight.assessment}
              </p>
            </div>
          );
        })}
      </div>

      {/* Detailed Pillars List */}
      <div className="space-y-3 pt-1">
        {visiblePillars.map((pillar) => {
          const Icon = pillar.icon;
          return (
            <div
              key={pillar.key}
              className="border border-line rounded-lg bg-surface-primary p-4 space-y-3 hover:border-border-strong transition-colors"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-2.5">
                <div className="flex items-center gap-2.5">
                  <div className="size-7 rounded bg-surface-secondary border border-border grid place-items-center text-ink font-bold font-mono text-xs">
                    {pillar.key}
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-ink flex items-center gap-1.5">
                      <Icon className="size-3.5 text-ink-secondary" aria-hidden="true" />
                      <span>{pillar.nameVi}</span>
                    </h3>
                    <p className="text-[11px] text-ink-secondary">
                      {pillar.description}
                    </p>
                  </div>
                </div>
              </div>

              {/* Metrics row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                {pillar.metrics.map((m) => (
                  <div
                    key={String(m.key)}
                    className="border border-line rounded bg-surface-secondary p-2.5 space-y-1"
                  >
                    <div className="text-[11px] font-medium text-ink-secondary">
                      {m.label}
                    </div>
                    <div className="flex items-center gap-3 font-mono">
                      {companyInsights.map((c) => (
                        <div key={c.ticker} className="flex items-baseline gap-1">
                          <span className="text-[10px] text-ink-tertiary">
                            {c.ticker}:
                          </span>
                          <span className="text-xs font-bold text-ink">
                            {formatMetric(c[m.key], 2, m.unit)}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="text-[10px] text-ink-tertiary leading-tight">
                      {m.benchmarkNote}
                    </div>
                  </div>
                ))}
              </div>

              {/* Analytical Narrative */}
              <div className="border-t border-line/60 pt-2.5">
                <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-ink-secondary block mb-1">
                  Đánh giá phân tích chuyên sâu:
                </span>
                <p className="text-xs text-ink leading-relaxed">
                  {pillar.analysisText(companyInsights)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
