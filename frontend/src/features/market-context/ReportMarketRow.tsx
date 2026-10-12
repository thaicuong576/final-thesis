import React from 'react';
import { AlertCircle } from 'lucide-react';
import { useMarketValuation, useMarketQuotes } from './useMarketData';
import { useEquityReport } from '../equity-report/components/useEquityReport';
import type { AdaptiveReportResponse } from '../equity-report/model/types';
import type { BankValuation, MarketQuote } from './types';

export interface ReportMarketRowProps {
  report?: AdaptiveReportResponse;
  className?: string;
}

export const ReportMarketRow: React.FC<ReportMarketRowProps> = ({ report: propReport, className = '' }) => {
  // Can use context or prop
  let contextReport: AdaptiveReportResponse | null = null;
  try {
    const ctx = useEquityReport();
    contextReport = ctx.report;
  } catch {
    // If rendered outside provider
  }

  const report = propReport || contextReport;
  const { data: valData } = useMarketValuation();
  const { data: quotesData } = useMarketQuotes();

  // 5. Unconfigured or empty-and-down states: everything market-related disappears cleanly with no empty frames
  if (!valData || !valData.configured || !valData.items || valData.items.length === 0) {
    return null;
  }

  if (!report) {
    return null;
  }

  const isStale = valData.stale || quotesData?.stale;

  // Determine focal bank(s)
  // Company / peer reports: the subject
  // Sector / ranking reports: the top and bottom of ranking by requested metric, or focal entity if plan has one
  const focalEntities: Array<{ ticker: string; roleLabel?: string }> = [];

  const targetTicker =
    (typeof report.target_ticker === 'string' && report.target_ticker.trim()) ||
    (report as { report_spec?: { target_ticker?: string } })?.report_spec?.target_ticker ||
    '';

  const questionType = (report as { question_type?: string })?.question_type || '';
  const isRankingOrSector = questionType === 'ranking' || questionType === 'sector_theme';

  if (targetTicker) {
    focalEntities.push({ ticker: targetTicker.toUpperCase() });
  } else if (isRankingOrSector) {
    // Find top and bottom of ranking from facts
    const rankFacts = (report.facts || []).filter(
      (f) => f.fact_type === 'peer_rank' && Boolean(f.entity_id)
    );

    if (rankFacts.length > 0) {
      const sortedRanks = [...rankFacts].sort((a, b) => {
        const ra = a.rank_better ?? Number(a.value ?? 999);
        const rb = b.rank_better ?? Number(b.value ?? 999);
        return ra - rb;
      });
      const topFact = sortedRanks[0];
      const bottomFact = sortedRanks[sortedRanks.length - 1];

      if (topFact?.entity_id) {
        focalEntities.push({
          ticker: topFact.entity_id.toUpperCase(),
          roleLabel: 'Đầu nhóm',
        });
      }
      if (bottomFact?.entity_id && bottomFact.entity_id.toUpperCase() !== topFact?.entity_id?.toUpperCase()) {
        focalEntities.push({
          ticker: bottomFact.entity_id.toUpperCase(),
          roleLabel: 'Cuối nhóm',
        });
      }
    }
  }

  // Fallback: first entity with a value fact
  if (focalEntities.length === 0) {
    const firstVal = (report.facts || []).find((f) => f.fact_type === 'value' && Boolean(f.entity_id));
    if (firstVal?.entity_id) {
      focalEntities.push({ ticker: firstVal.entity_id.toUpperCase() });
    }
  }

  if (focalEntities.length === 0) {
    return null;
  }

  const formatTime = (iso?: string | null): string => {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return '';
    }
  };

  const updatedTime = formatTime(quotesData?.fetched_at || valData.fetched_at);

  return (
    <div
      role="region"
      aria-label="Bối cảnh thị trường trong báo cáo"
      className={`mt-5 space-y-4 ${className}`}
    >
      {focalEntities.map(({ ticker, roleLabel }) => {
        const valItem: BankValuation | undefined = valData.items.find(
          (item) => item.ticker.toUpperCase() === ticker
        );
        const quoteItem: MarketQuote | undefined = quotesData?.quotes?.find(
          (q) => q.ticker.toUpperCase() === ticker
        );

        if (!valItem && !quoteItem) return null;

        const closePrice = valItem?.close ?? quoteItem?.close ?? null;
        const change = quoteItem?.change ?? 0;
        const changePercent = quoteItem?.change_percent ?? 0;
        const pb = valItem?.pb ?? null;
        const roe = valItem?.roe ?? null;
        const isUp = change > 0;
        const isDown = change < 0;
        const tradingDate = quoteItem?.trading_date || valItem?.inputs?.close_date || '';

        const changeColor = isUp
          ? 'text-text-success'
          : isDown
          ? 'text-danger'
          : 'text-text-tertiary';

        return (
          <div key={ticker} className="space-y-2">
            {/* Row Label Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-text-tertiary">
                  Thị trường
                </span>
                <span className="rounded bg-surface-secondary border border-border-subtle px-1.5 py-0.5 font-mono text-xs font-bold text-text-primary">
                  {ticker}
                </span>
                {roleLabel && (
                  <span className="text-xs text-text-secondary">({roleLabel})</span>
                )}
              </div>
              {isStale && (
                <span className="inline-flex items-center gap-1 text-[10px] font-sans font-medium text-text-accent bg-amber-soft px-1.5 py-0.5 rounded border border-amber/30">
                  <AlertCircle className="w-2.5 h-2.5" />
                  <span>dữ liệu trễ</span>
                </span>
              )}
            </div>

            {/* KPI-style 4-tile band */}
            <div
              className="grid grid-cols-2 sm:grid-cols-4 overflow-hidden rounded-xl border border-border-subtle bg-surface-primary"
              role="group"
              aria-label={`Chỉ số thị trường của ${ticker}`}
            >
              {/* Tile 1: Giá đóng cửa */}
              <div className="p-4 border-border-subtle">
                <p className="m-0 text-xs font-medium text-text-tertiary">Giá đóng cửa</p>
                <p className="mt-1.5 mb-1 text-[26px] font-semibold leading-none tabular-nums font-mono text-text-primary">
                  {closePrice != null ? `${closePrice.toLocaleString('vi-VN')} đ` : '—'}
                </p>
                <p className="m-0 text-xs tabular-nums text-text-tertiary">
                  {tradingDate ? `Phiên ${tradingDate}` : 'Giá chốt phiên'}
                </p>
              </div>

              {/* Tile 2: Biến động phiên */}
              <div className="p-4 border-l border-border-subtle">
                <p className="m-0 text-xs font-medium text-text-tertiary">Biến động phiên</p>
                <p className={`mt-1.5 mb-1 text-[26px] font-semibold leading-none tabular-nums font-mono ${changeColor}`}>
                  {change > 0 ? '+' : ''}
                  {changePercent.toFixed(2)}%
                </p>
                <p className="m-0 text-xs tabular-nums text-text-tertiary">
                  {change > 0
                    ? `▲ Tăng ${Math.abs(change).toLocaleString('vi-VN')} đ`
                    : change < 0
                    ? `▼ Giảm ${Math.abs(change).toLocaleString('vi-VN')} đ`
                    : 'Không đổi'}
                </p>
              </div>

              {/* Tile 3: P/B */}
              <div className="p-4 border-t sm:border-t-0 sm:border-l border-border-subtle">
                <p className="m-0 text-xs font-medium text-text-tertiary">P/B (Định giá)</p>
                <p className="mt-1.5 mb-1 text-[26px] font-semibold leading-none tabular-nums font-mono text-text-accent">
                  {pb != null ? `${pb.toFixed(2)}x` : '—'}
                </p>
                <p className="m-0 text-xs tabular-nums text-text-tertiary">
                  Giá / Giá trị sổ sách
                </p>
              </div>

              {/* Tile 4: ROE */}
              <div className="p-4 border-t sm:border-t-0 border-l border-border-subtle">
                <p className="m-0 text-xs font-medium text-text-tertiary">ROE (BCTC)</p>
                <p className="mt-1.5 mb-1 text-[26px] font-semibold leading-none tabular-nums font-mono text-text-primary">
                  {roe != null ? `${roe.toFixed(2)}%` : '—'}
                </p>
                <p className="m-0 text-xs tabular-nums text-text-tertiary">
                  {valItem?.inputs?.roe_period
                    ? `Kỳ ${valItem.inputs.roe_period.replace(/^(\d{4})_Q(\d)$/, 'Q$2/$1')}`
                    : 'Cùng kỳ BCTC'}
                </p>
              </div>
            </div>

            {/* Quiet Footer Line */}
            <p className="m-0 text-[11px] font-mono text-text-tertiary leading-relaxed">
              Nguồn: SSI FastConnect Data {tradingDate ? `· Phiên ${tradingDate}` : ''} {updatedTime ? `· Giờ cập nhật ${updatedTime}` : ''} · Tham khảo ngoài báo cáo thẩm định
            </p>
          </div>
        );
      })}
    </div>
  );
};
