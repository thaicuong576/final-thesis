import React from "react";
import { TrendingUp, TrendingDown, Info, AlertCircle } from "lucide-react";
import { useMarketValuation, useMarketQuotes } from "./useMarketData";
import type { BankValuation, MarketQuote } from "./types";

interface FocalValuationCardProps {
  ticker?: string | null;
  className?: string;
}

export const FocalValuationCard: React.FC<FocalValuationCardProps> = ({
  ticker,
  className = "",
}) => {
  const { data: valData } = useMarketValuation();
  const { data: quotesData } = useMarketQuotes();

  if (!ticker || !valData || !valData.configured) {
    return null;
  }

  const focalTicker = ticker.toUpperCase();
  const valItem: BankValuation | undefined = valData.items?.find(
    (item) => item.ticker.toUpperCase() === focalTicker
  );
  const quoteItem: MarketQuote | undefined = quotesData?.quotes?.find(
    (q) => q.ticker.toUpperCase() === focalTicker
  );

  if (!valItem && !quoteItem) {
    return null;
  }

  const closePrice = valItem?.close ?? quoteItem?.close ?? null;
  const change = quoteItem?.change ?? 0;
  const changePercent = quoteItem?.change_percent ?? 0;
  const pb = valItem?.pb ?? null;
  const roe = valItem?.roe ?? null;
  const isUp = change > 0;
  const isDown = change < 0;
  const isStale = valData.stale || quotesData?.stale;

  const tradingDate = quoteItem?.trading_date || valItem?.inputs?.close_date || "";

  return (
    <div
      role="complementary"
      aria-label={`Bối cảnh thị trường cho ${focalTicker}`}
      className={`p-4 bg-white dark:bg-[#1E1E1E] border border-[#E5E3DC] dark:border-[#333] rounded-lg shadow-2xs space-y-3 ${className}`}
    >
      <div className="flex items-center justify-between gap-2 border-b border-[#F0EFEA] dark:border-[#2A2A2A] pb-2.5">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-xs font-bold font-mono bg-[#B45309] text-white rounded">
            {focalTicker}
          </span>
          <span className="text-xs font-semibold text-[#1C1B18] dark:text-[#F0F0F0]">
            Bối cảnh thị trường & Định giá
          </span>
        </div>
        {isStale && (
          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 px-1.5 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            <AlertCircle className="w-2.5 h-2.5" />
            <span>dữ liệu trễ</span>
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-0.5">
        {/* Close Price */}
        <div className="space-y-0.5">
          <span className="text-[10px] uppercase font-mono text-[#8C8A82]">Giá đóng cửa</span>
          <div className="text-sm sm:text-base font-bold font-mono text-[#1C1B18] dark:text-[#F0F0F0]">
            {closePrice != null ? `${closePrice.toLocaleString("vi-VN")} đ` : "—"}
          </div>
        </div>

        {/* Change */}
        <div className="space-y-0.5">
          <span className="text-[10px] uppercase font-mono text-[#8C8A82]">Biến động phiên</span>
          <div
            className={`text-sm sm:text-base font-bold font-mono flex items-center gap-1 ${
              isUp
                ? "text-emerald-700 dark:text-emerald-400"
                : isDown
                ? "text-rose-700 dark:text-rose-400"
                : "text-[#6B6960] dark:text-[#999]"
            }`}
          >
            {isUp ? <TrendingUp className="w-3.5 h-3.5" /> : isDown ? <TrendingDown className="w-3.5 h-3.5" /> : null}
            <span>
              {change > 0 ? "+" : ""}
              {changePercent.toFixed(2)}%
            </span>
          </div>
        </div>

        {/* P/B Valuation */}
        <div className="space-y-0.5">
          <span className="text-[10px] uppercase font-mono text-[#8C8A82]" title="Price-to-Book ratio">
            P/B (Định giá)
          </span>
          <div className="text-sm sm:text-base font-bold font-mono text-[#B45309] dark:text-[#D97706]">
            {pb != null ? `${pb.toFixed(2)}x` : <span className="text-[#8C8A82] text-xs font-normal" title={valItem?.missing_reason || "Thiếu dữ liệu"}>Chưa đủ dữ liệu</span>}
          </div>
        </div>

        {/* ROE */}
        <div className="space-y-0.5">
          <span className="text-[10px] uppercase font-mono text-[#8C8A82]" title="Tỷ suất sinh lời trên vốn CSH kỳ gần nhất">
            ROE (BCTC)
          </span>
          <div className="text-sm sm:text-base font-bold font-mono text-[#1C1B18] dark:text-[#F0F0F0]">
            {roe != null ? `${roe.toFixed(2)}%` : "—"}
          </div>
        </div>
      </div>

      {/* Attribution & Context Disclaimer */}
      <div className="pt-2 border-t border-[#F0EFEA] dark:border-[#2A2A2A] flex items-center justify-between text-[11px] text-[#8C8A82] dark:text-[#888] font-mono">
        <div className="flex items-center gap-1.5">
          <Info className="w-3 h-3 text-[#B45309] shrink-0" />
          <span>
            Nguồn: SSI FastConnect Data {tradingDate ? `(phiên ${tradingDate})` : ""} · Tham khảo ngoài báo cáo thẩm định
          </span>
        </div>
      </div>
    </div>
  );
};
