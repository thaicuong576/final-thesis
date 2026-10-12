import React from "react";
import { Clock, AlertCircle } from "lucide-react";
import { useMarketQuotes } from "./useMarketData";
import type { MarketQuote } from "./types";

interface MarketPriceStripProps {
  className?: string;
}

export const MarketPriceStrip: React.FC<MarketPriceStripProps> = ({ className = "" }) => {
  const { data } = useMarketQuotes();

  // If unconfigured or loading with no data yet, do not render (no layout shift)
  if (!data || !data.configured) {
    return null;
  }

  // First load with SSI down / empty cache: show one-line message and nothing that looks like prices
  if (!data.quotes || data.quotes.length === 0) {
    return (
      <div
        role="region"
        aria-label="Thông báo dữ liệu thị trường"
        className={`w-full bg-[#FAF9F5] dark:bg-[#1E1E1E] border-b border-[#E5E3DC] dark:border-[#333] px-3 sm:px-6 py-1.5 text-xs text-[#6B6960] dark:text-[#999] select-none transition-colors motion-reduce:transition-none ${className}`}
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
            <span className="font-medium text-[#1C1B18] dark:text-[#E0E0E0]">
              Dữ liệu thị trường tạm thời không khả dụng
            </span>
          </div>
          {data.stale_reason && (
            <span className="text-[11px] text-[#8C8A82] dark:text-[#777] hidden sm:inline font-mono">
              ({data.stale_reason})
            </span>
          )}
        </div>
      </div>
    );
  }

  const { quotes, stale, stale_reason, fetched_at } = data;

  // Format time hh:mm:ss from fetched_at
  const formatTime = (iso?: string | null): string => {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return "";
    }
  };

  const updatedTime = formatTime(fetched_at);
  const tradingDate = quotes[0]?.trading_date || "";

  return (
    <div
      role="region"
      aria-label="Bảng giá thị trường SSI 10 ngân hàng HOSE"
      className={`w-full bg-[#FAF9F5] dark:bg-[#1E1E1E] border-b border-[#E5E3DC] dark:border-[#333] px-3 sm:px-6 py-1.5 text-xs text-[#1C1B18] dark:text-[#E0E0E0] select-none transition-colors motion-reduce:transition-none ${className}`}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-2 overflow-x-auto scrollbar-none">
        {/* Ticker Quotes List */}
        <div className="flex items-center gap-3 sm:gap-4 shrink-0">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#B45309] dark:text-[#D97706] shrink-0 font-mono">
            HOSE
          </span>
          <div className="flex items-center gap-3 sm:gap-4 shrink-0 font-mono">
            {quotes.map((q: MarketQuote) => {
              const isUp = q.change > 0;
              const isDown = q.change < 0;
              const changeSign = isUp ? "+" : "";
              const colorClass = isUp
                ? "text-emerald-700 dark:text-emerald-400 font-semibold"
                : isDown
                ? "text-rose-700 dark:text-rose-400 font-semibold"
                : "text-[#6B6960] dark:text-[#999]";

              return (
                <div
                  key={q.ticker}
                  className="flex items-center gap-1.5 shrink-0 text-[11px]"
                  title={`${q.ticker}: Đóng cửa ${q.close.toLocaleString("vi-VN")} VND (${changeSign}${q.change_percent.toFixed(2)}%)`}
                >
                  <span className="font-bold text-[#1C1B18] dark:text-[#F0F0F0]">
                    {q.ticker}
                  </span>
                  <span>{q.close.toLocaleString("vi-VN")}</span>
                  <span className={colorClass}>
                    {changeSign}
                    {q.change_percent.toFixed(2)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Metadata info: trading date, updated time, stale badge */}
        <div className="flex items-center gap-2 shrink-0 text-[10px] text-[#8C8A82] dark:text-[#888] font-mono pl-3 border-l border-[#E5E3DC] dark:border-[#333]">
          {stale && (
            <span
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-700 font-sans font-medium"
              title={stale_reason ? `Dữ liệu trễ: ${stale_reason}` : "Dữ liệu phiên trước hoặc kết nối trễ"}
            >
              <AlertCircle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
              <span>dữ liệu trễ</span>
            </span>
          )}

          {tradingDate && (
            <span className="hidden md:inline">
              Phiên {tradingDate}
            </span>
          )}

          {updatedTime && (
            <span className="inline-flex items-center gap-1">
              <Clock className="w-2.5 h-2.5 text-[#8C8A82]" />
              <span>cập nhật {updatedTime}</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
