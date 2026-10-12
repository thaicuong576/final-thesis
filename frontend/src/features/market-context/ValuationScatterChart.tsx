import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Info, HelpCircle } from 'lucide-react';
import { useMarketValuation, useMarketQuotes } from './useMarketData';
import { useEquityReport } from '../equity-report/components/useEquityReport';
import type { AdaptiveReportResponse } from '../equity-report/model/types';
import type { BankValuation } from './types';

export interface ValuationScatterChartProps {
  focalTicker?: string | null;
  report?: AdaptiveReportResponse | null;
  className?: string;
  defaultExpanded?: boolean;
}

export const ValuationScatterChart: React.FC<ValuationScatterChartProps> = ({
  focalTicker: propFocalTicker,
  report: propReport,
  className = '',
  defaultExpanded = false,
}) => {
  const { data: valData } = useMarketValuation();
  const { data: quotesData } = useMarketQuotes();
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [hoveredBank, setHoveredBank] = useState<BankValuation | null>(null);

  let contextReport: AdaptiveReportResponse | null = null;
  try {
    const ctx = useEquityReport();
    contextReport = ctx.report;
  } catch {
    // Rendered outside EquityReportProvider
  }

  const report = propReport || contextReport;

  if (!valData || !valData.configured || !valData.items || valData.items.length === 0) {
    return null;
  }

  // Filter valid points with both P/B and ROE
  const validPoints = valData.items.filter(
    (b) => b.pb != null && b.roe != null && !isNaN(b.pb) && !isNaN(b.roe)
  );

  if (validPoints.length === 0) {
    return null;
  }

  const targetTicker =
    propFocalTicker ||
    (typeof report?.target_ticker === 'string' && report.target_ticker.trim()) ||
    (report as { report_spec?: { target_ticker?: string } })?.report_spec?.target_ticker ||
    null;

  const focalUpper = targetTicker ? targetTicker.toUpperCase() : null;
  const questionType = report?.question_type || '';
  const isRankingOrSector = questionType === 'ranking' || questionType === 'sector_theme';

  // Chart layout dimensions
  const chartW = 560;
  const chartH = 280;
  const leftM = 48;
  const rightM = 32;
  const topM = 24;
  const bottomM = 36;

  const plotW = chartW - leftM - rightM;
  const plotH = chartH - topM - bottomM;

  // Bounds
  const roeValues = validPoints.map((p) => p.roe!);
  const pbValues = validPoints.map((p) => p.pb!);

  const minRoe = Math.max(0, Math.floor(Math.min(...roeValues) - 2));
  const maxRoe = Math.ceil(Math.max(...roeValues) + 2);
  const minPb = Math.max(0, Math.floor((Math.min(...pbValues) - 0.2) * 10) / 10);
  const maxPb = Math.ceil((Math.max(...pbValues) + 0.3) * 10) / 10;

  const scaleX = (roe: number) => {
    return leftM + ((roe - minRoe) / (maxRoe - minRoe || 1)) * plotW;
  };

  const scaleY = (pb: number) => {
    return topM + plotH - ((pb - minPb) / (maxPb - minPb || 1)) * plotH;
  };

  // Ticks
  const xTicks = [minRoe, Math.round((minRoe + maxRoe) / 2), maxRoe];
  const yTicks = [minPb, Math.round(((minPb + maxPb) / 2) * 10) / 10, maxPb];

  // STB Footnote logic:
  // Data-driven: show the note only when ROE is more than 8 points below the peer median
  const sortedRoes = [...roeValues].sort((a, b) => a - b);
  const medianRoe =
    sortedRoes.length % 2 === 0
      ? (sortedRoes[sortedRoes.length / 2 - 1] + sortedRoes[sortedRoes.length / 2]) / 2
      : sortedRoes[Math.floor(sortedRoes.length / 2)];

  const stbPoint = validPoints.find((p) => p.ticker.toUpperCase() === 'STB');
  const showStbFootnote = Boolean(stbPoint && stbPoint.roe != null && medianRoe - stbPoint.roe > 8);

  return (
    <section
      aria-label="Bối cảnh thị trường: P/B so với ROE"
      className={`border border-border-subtle bg-surface-primary rounded-xl shadow-2xs overflow-hidden ${className}`}
    >
      {/* Collapsible Header */}
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="w-full px-4 py-3 bg-surface-secondary border-b border-border-subtle flex items-center justify-between gap-3 text-left transition-colors hover:bg-surface-tertiary/60 cursor-pointer"
        aria-expanded={isExpanded}
      >
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-amber shrink-0" />
          <div>
            <h4 className="text-xs font-semibold text-text-primary">
              Bối cảnh thị trường: Định giá P/B so với ROE 10 ngân hàng HOSE
            </h4>
            <p className="text-[11px] text-text-tertiary">
              Dữ liệu giá thị trường SSI FastConnect và BCTC kỳ gần nhất · Tham khảo ngoài báo cáo thẩm định
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-text-accent font-medium shrink-0">
          <span>{isExpanded ? 'Thu gọn' : 'Xem đồ thị'}</span>
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded Chart Body */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Sector / Ranking reports without a single focal bank: compact 10-ticker chips */}
          {(!focalUpper || isRankingOrSector) && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-text-secondary">
                Bảng giá &amp; định giá 10 ngân hàng HOSE
              </p>
              <div
                className="grid grid-cols-2 sm:grid-cols-5 gap-2"
                role="group"
                aria-label="Thống kê định giá 10 ngân hàng"
              >
                {valData.items.map((b) => {
                  const q = quotesData?.quotes?.find(
                    (quote) => quote.ticker.toUpperCase() === b.ticker.toUpperCase()
                  );
                  const changePct = q?.change_percent ?? 0;
                  const isUp = changePct > 0;
                  const isDown = changePct < 0;
                  const changeColor = isUp
                    ? 'text-text-success'
                    : isDown
                    ? 'text-danger'
                    : 'text-text-tertiary';

                  return (
                    <div
                      key={b.ticker}
                      className="flex flex-col p-2.5 rounded-lg bg-surface-secondary border border-border-subtle text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-text-primary">{b.ticker}</span>
                        <span className={`font-mono text-[11px] font-medium ${changeColor}`}>
                          {isUp ? '+' : ''}
                          {changePct.toFixed(2)}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between mt-1 text-[11px] tabular-nums font-mono text-text-secondary">
                        <span>{b.close != null ? `${b.close.toLocaleString('vi-VN')} đ` : '—'}</span>
                        <span className="text-text-accent font-semibold">
                          {b.pb != null ? `${b.pb.toFixed(2)}x` : '—'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Scatter Plot SVG */}
          <div className="relative overflow-x-auto">
            <svg
              viewBox={`0 0 ${chartW} ${chartH}`}
              className="w-full max-w-[560px] mx-auto overflow-visible select-none"
            >
              {/* Axes lines */}
              <line
                x1={leftM}
                y1={topM + plotH}
                x2={leftM + plotW}
                y2={topM + plotH}
                stroke="#D6D3D1"
                strokeWidth={1}
              />
              <line
                x1={leftM}
                y1={topM}
                x2={leftM}
                y2={topM + plotH}
                stroke="#D6D3D1"
                strokeWidth={1}
              />

              {/* Y Axis Ticks */}
              {yTicks.map((yVal) => (
                <g key={`y-${yVal}`}>
                  <line
                    x1={leftM - 4}
                    y1={scaleY(yVal)}
                    x2={leftM + plotW}
                    y2={scaleY(yVal)}
                    stroke="#F5F5F4"
                    strokeDasharray="2,2"
                  />
                  <text
                    x={leftM - 8}
                    y={scaleY(yVal) + 4}
                    textAnchor="end"
                    fontSize={10}
                    fontFamily="monospace"
                    fill="#78716C"
                  >
                    {yVal.toFixed(1)}x
                  </text>
                </g>
              ))}

              {/* X Axis Ticks */}
              {xTicks.map((xVal) => (
                <g key={`x-${xVal}`}>
                  <line
                    x1={scaleX(xVal)}
                    y1={topM}
                    x2={scaleX(xVal)}
                    y2={topM + plotH + 4}
                    stroke="#F5F5F4"
                    strokeDasharray="2,2"
                  />
                  <text
                    x={scaleX(xVal)}
                    y={topM + plotH + 18}
                    textAnchor="middle"
                    fontSize={10}
                    fontFamily="monospace"
                    fill="#78716C"
                  >
                    {xVal}%
                  </text>
                </g>
              ))}

              {/* Axis Titles */}
              <text
                x={leftM + plotW / 2}
                y={chartH - 4}
                textAnchor="middle"
                fontSize={10}
                fontWeight="bold"
                fill="#44403C"
              >
                ROE (% - Báo cáo tài chính)
              </text>
              <text
                x={12}
                y={topM + plotH / 2}
                textAnchor="middle"
                transform={`rotate(-90, 12, ${topM + plotH / 2})`}
                fontSize={10}
                fontWeight="bold"
                fill="#44403C"
              >
                P/B (lần)
              </text>

              {/* Scatter Points */}
              {validPoints.map((b) => {
                const cx = scaleX(b.roe!);
                const cy = scaleY(b.pb!);
                const isFocal = focalUpper ? b.ticker.toUpperCase() === focalUpper : false;
                const isHovered = hoveredBank?.ticker === b.ticker;

                return (
                  <g
                    key={b.ticker}
                    className="cursor-pointer transition-transform"
                    onMouseEnter={() => setHoveredBank(b)}
                    onMouseLeave={() => setHoveredBank(null)}
                  >
                    {/* Highlight Ring for focal bank */}
                    {isFocal && (
                      <circle
                        cx={cx}
                        cy={cy}
                        r={12}
                        fill="#B45309"
                        fillOpacity={0.15}
                        stroke="#B45309"
                        strokeWidth={1.5}
                        strokeDasharray="3,3"
                      />
                    )}

                    {/* Point Circle */}
                    <circle
                      cx={cx}
                      cy={cy}
                      r={isFocal ? 7 : isHovered ? 6 : 4.5}
                      fill={isFocal ? '#B45309' : '#FFFFFF'}
                      stroke="#B45309"
                      strokeWidth={isFocal ? 2.5 : 1.5}
                      className="transition-all motion-reduce:transition-none"
                    />

                    {/* Bank Ticker Label */}
                    <text
                      x={cx + 8}
                      y={cy + 3}
                      fontSize={isFocal ? 11 : 9.5}
                      fontWeight={isFocal ? 'bold' : 'normal'}
                      fontFamily="monospace"
                      fill={isFocal ? '#B45309' : '#1C1917'}
                    >
                      {b.ticker}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Hover / Focal Bank Details Box */}
          {hoveredBank && (
            <div className="p-3 bg-surface-secondary border border-border-subtle rounded-lg text-xs space-y-1.5 animate-in fade-in duration-100">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-bold font-mono px-1.5 py-0.5 bg-amber text-white rounded text-[11px]">
                    {hoveredBank.ticker}
                  </span>
                  <span className="font-semibold text-text-primary">
                    P/B: {hoveredBank.pb?.toFixed(2)}x · ROE: {hoveredBank.roe?.toFixed(2)}%
                  </span>
                </div>
                {hoveredBank.ticker.toUpperCase() === focalUpper && (
                  <span className="text-[10px] text-text-accent font-bold">Ngân hàng trọng tâm</span>
                )}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-text-secondary font-mono pt-1">
                <div>
                  Giá: <strong className="text-text-primary">{hoveredBank.close?.toLocaleString('vi-VN')} đ</strong>
                </div>
                <div>
                  Số CP: <strong className="text-text-primary">{hoveredBank.listed_shares?.toLocaleString('vi-VN')}</strong>
                </div>
                <div>
                  Vốn CSH mẹ:{' '}
                  <strong className="text-text-primary">
                    {hoveredBank.parent_attributable_equity?.toLocaleString('vi-VN')} tỷ đ
                  </strong>
                </div>
                <div>
                  BVPS: <strong className="text-text-primary">{hoveredBank.bvps?.toLocaleString('vi-VN')} đ</strong>
                </div>
              </div>
            </div>
          )}

          {/* Footnotes */}
          <div className="pt-2 border-t border-border-subtle text-[10px] text-text-tertiary space-y-1">
            {showStbFootnote && (
              <p className="leading-relaxed font-sans text-text-secondary font-medium">
                * STB: ROE thấp hơn nhóm.
              </p>
            )}
            <p className="flex items-start gap-1">
              <HelpCircle className="w-3 h-3 text-amber shrink-0 mt-0.5" />
              <span>
                Công thức: P/B = Giá đóng cửa / (Vốn CSH ngân hàng mẹ × 10⁹ / Số cổ phiếu niêm yết). Số cổ phiếu niêm yết, chưa trừ cổ phiếu quỹ.
              </span>
            </p>
            <p>
              * Bối cảnh thị trường tham khảo bên cạnh báo cáo thẩm định, không tham gia vào cấu trúc sự kiện (facts) hay quyết định thẩm định độc lập.
            </p>
          </div>
        </div>
      )}
    </section>
  );
};
