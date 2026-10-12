import React from 'react';
import { AlertCircle, Clock } from 'lucide-react';
import { useMarketQuotes } from './useMarketData';
import type { MarketQuote } from './types';

interface MarketPriceStripProps {
  className?: string;
}

export const MarketPriceStrip: React.FC<MarketPriceStripProps> = ({ className = '' }) => {
  const { data } = useMarketQuotes();

  // 5. Unconfigured or empty-and-down states: everything market-related disappears cleanly with no empty frames
  if (!data || !data.configured || !data.quotes || data.quotes.length === 0) {
    return null;
  }

  const { quotes, stale, stale_reason, fetched_at } = data;

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

  const updatedTime = formatTime(fetched_at);
  const tradingDate = quotes[0]?.trading_date || '';

  const renderQuoteItem = (q: MarketQuote, idx: number, suffix: string = '') => {
    const isUp = q.change > 0;
    const isDown = q.change < 0;
    const changeSign = isUp ? '+' : '';
    const colorClass = isUp
      ? 'text-text-success font-semibold'
      : isDown
      ? 'text-danger font-semibold'
      : 'text-text-tertiary';

    return (
      <div
        key={`${q.ticker}-${suffix}-${idx}`}
        className="flex items-center gap-1.5 shrink-0 px-2 py-0.5"
        title={`${q.ticker}: Đóng cửa ${q.close.toLocaleString('vi-VN')} VND (${changeSign}${q.change_percent.toFixed(2)}%)`}
      >
        <span className="font-bold text-text-primary">{q.ticker}</span>
        <span className="text-text-primary tabular-nums">{q.close.toLocaleString('vi-VN')}</span>
        <span className={`${colorClass} tabular-nums`}>
          {changeSign}
          {q.change_percent.toFixed(2)}%
        </span>
      </div>
    );
  };

  return (
    <div
      role="region"
      aria-label="Bảng giá thị trường SSI 10 ngân hàng HOSE"
      className={`ticker-container w-full border-t border-border-subtle/80 bg-surface-primary/95 text-xs text-text-primary select-none overflow-hidden hidden sm:block ${className}`}
    >
      <div className="flex items-center justify-between px-4 sm:px-6 py-1 gap-3">
        {/* Left prefix badge */}
        <div className="flex items-center gap-2 shrink-0 pr-2 border-r border-border-subtle z-10 bg-surface-primary/95">
          <span className="text-[10px] font-bold uppercase tracking-wider text-accent font-mono">
            HOSE
          </span>
          {stale && (
            <span
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-soft text-text-accent border border-amber/30 text-[10px] font-sans font-medium shrink-0"
              title={stale_reason ? `Dữ liệu trễ: ${stale_reason}` : 'Dữ liệu phiên trước hoặc kết nối trễ'}
            >
              <AlertCircle className="w-2.5 h-2.5 text-accent" />
              <span>dữ liệu trễ</span>
            </span>
          )}
        </div>

        {/* Marquee ticker track */}
        <div className="flex-1 overflow-hidden font-mono text-[11px] relative">
          <div className="ticker-track items-center">
            {/* First copy */}
            <div className="flex items-center gap-2 shrink-0">
              {quotes.map((q, idx) => renderQuoteItem(q, idx, 'a'))}
            </div>
            <span className="text-text-tertiary px-2" aria-hidden="true">·</span>
            {/* Duplicate copy for continuous seamless marquee */}
            <div className="flex items-center gap-2 shrink-0" aria-hidden="true">
              {quotes.map((q, idx) => renderQuoteItem(q, idx, 'b'))}
            </div>
          </div>
        </div>

        {/* Right meta info */}
        <div className="flex items-center gap-2 shrink-0 text-[10px] text-text-tertiary font-mono pl-3 border-l border-border-subtle z-10 bg-surface-primary/95">
          {tradingDate && (
            <span className="hidden md:inline">
              Phiên {tradingDate}
            </span>
          )}
          {updatedTime && (
            <span className="inline-flex items-center gap-1">
              <Clock className="w-2.5 h-2.5 text-text-tertiary" />
              <span>cập nhật {updatedTime}</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
