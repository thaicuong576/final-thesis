import React, { useState } from 'react';
import type { NormalizedFigureBlock } from '../model/normalizeBlocks';
import { useEquityReport } from './useEquityReport';
import { CHARTS, DataTable } from '../charts';
import { SentenceView } from './SentenceView';
import { formatDisplayText } from '@/shared/lib/formatting';

export const Figure: React.FC<{ block: NormalizedFigureBlock }> = ({ block }) => {
  const { datasets, metrics, highlight } = useEquityReport();
  const [showTable, setShowTable] = useState(false);

  const dataset = datasets.find((d) => d.dataset_id === block.dataset_id) || {
    dataset_id: block.dataset_id,
    shape: 'kpi',
    title: block.title,
    produced_by: { tool: 'unknown', agent: 'system' },
    metric_ids: [],
    periods: [],
    highlight_entity_ids: highlight,
    rows: [],
    reference_lines: [],
    allowed_charts: []
  };

  const ChartComponent = CHARTS[block.chart] || DataTable;
  const takeaways = [block.takeaway, ...(block.extra_takeaways || [])].filter(Boolean);

  return (
    <figure className="my-6 p-0 font-sans break-inside-avoid max-w-full overflow-hidden">
      {/* Caption */}
      <figcaption className="text-[13px] text-text-secondary mb-3">
        <b className="font-semibold text-text-primary">Hình {block.figure_no}.</b> {formatDisplayText(block.title)}
      </figcaption>

      {/* Chart Body or Table View */}
      <div className="-mx-1 overflow-x-auto px-1">
        {showTable ? (
          <DataTable dataset={dataset} metrics={metrics} highlight={highlight} />
        ) : (
          <ChartComponent dataset={dataset} metrics={metrics} highlight={highlight} />
        )}
      </div>

      {takeaways.length > 0 && (
        <div className="mt-3 space-y-1 text-[13px] leading-relaxed text-text-primary">
          {takeaways.map((t, idx) => (
            <p key={t.sentence_id || idx} className="m-0">
              <SentenceView sentence={t} />
            </p>
          ))}
        </div>
      )}

      {/* Source Line and Toggle Table Button */}
      <div className="flex items-baseline justify-between gap-2 mt-1.5 text-[11px] text-text-muted">
        <span>
          Nguồn: BCTC hợp nhất của các ngân hàng; hệ thống tính toán.
        </span>
        <button
          type="button"
          onClick={() => setShowTable((prev) => !prev)}
          className="text-text-accent hover:underline cursor-pointer bg-transparent border-none p-0 shrink-0 text-[11px] font-medium print:hidden"
        >
          {showTable ? 'Ẩn bảng số liệu' : 'Xem bảng số liệu'}
        </button>
      </div>
    </figure>
  );
};
