import React, { useState } from 'react';
import { useEquityReport } from './useEquityReport';

export const TechnicalDetails: React.FC = () => {
  const { report, facts } = useEquityReport();
  const [isOpen, setIsOpen] = useState(false);

  const audit = report.narrative_audit;
  const droppedSentences = audit?.sentences_dropped || [];
  const droppedBlocks = audit?.blocks_dropped || [];

  return (
    <div className="mt-4 pt-2 text-xs text-text-muted font-sans print:hidden">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="text-text-muted hover:text-text-primary font-medium flex items-center gap-1 cursor-pointer bg-transparent border-none p-0"
        aria-expanded={isOpen}
      >
        <span>{isOpen ? '▾' : '▸'}</span>
        <span>Chi tiết kỹ thuật</span>
      </button>

      {isOpen && (
        <div className="mt-3 p-4 bg-surface-secondary border border-line rounded space-y-4 font-mono text-[11px]">
          {/* Narrative Audit */}
          {audit && (
            <div>
              <div className="font-semibold text-text-primary mb-1.5 font-sans text-xs">
                Kiểm định văn bản (Narrative Audit)
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-text-secondary bg-surface-primary p-2.5 rounded border border-line">
                <div>
                  Câu kiểm tra:{' '}
                  <strong className="text-text-primary">{audit.sentences_checked}</strong>
                </div>
                <div>
                  Câu chấp nhận:{' '}
                  <strong className="text-text-primary">{audit.sentences_accepted}</strong>
                </div>
                <div>
                  Số kiểm tra:{' '}
                  <strong className="text-text-primary">{audit.numbers_checked}</strong>
                </div>
                <div>
                  Số khớp:{' '}
                  <strong className="text-text-primary">{audit.numbers_matched}</strong>
                </div>
              </div>

              {droppedSentences.length > 0 && (
                <div className="mt-2.5">
                  <div className="text-amber-800 font-semibold mb-1 font-sans">
                    Câu bị loại ({droppedSentences.length}):
                  </div>
                  <div className="space-y-1.5">
                    {droppedSentences.map((s, idx) => (
                      <div key={idx} className="p-2 bg-surface-primary border border-warning/40 rounded text-text-secondary">
                        <div className="text-text-primary line-through">{s.text}</div>
                        <div className="text-text-muted mt-0.5">
                          ID: {s.sentence_id} · Tác giả: {s.author} · Lý do: {s.reason} ({s.reason_code})
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {droppedBlocks.length > 0 && (
                <div className="mt-2.5">
                  <div className="text-amber-800 font-semibold mb-1 font-sans">
                    Khối bị bỏ ({droppedBlocks.length}):
                  </div>
                  <div className="space-y-1">
                    {droppedBlocks.map((b, idx) => (
                      <div key={idx} className="p-1.5 bg-surface-primary border border-line rounded">
                        Loại: {b.type} · Lý do: {b.reason}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Facts Table */}
          {facts.length > 0 && (
            <div>
              <div className="font-semibold text-text-primary mb-1.5 font-sans text-xs">
                Fact có nguồn và công thức ({facts.length})
              </div>
              <div className="overflow-x-auto max-h-60 border border-line rounded bg-surface-primary">
                <table className="w-full text-left border-collapse text-[10px]" role="table">
                  <thead>
                    <tr className="border-b border-line bg-surface-secondary text-text-muted">
                      <th className="p-1.5">Fact ID</th>
                      <th className="p-1.5">Chỉ tiêu</th>
                      <th className="p-1.5">Giá trị</th>
                      <th className="p-1.5">Công thức</th>
                      <th className="p-1.5">Observation IDs</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {facts.map((f) => (
                      <tr key={f.fact_id} className="hover:bg-surface-secondary/50">
                        <td className="p-1.5 font-bold text-text-primary">{f.fact_id}</td>
                        <td className="p-1.5">{f.metric_id}</td>
                        <td className="p-1.5 font-medium">{String(f.value)}</td>
                        <td className="p-1.5 text-text-secondary">{f.formula_version}</td>
                        <td className="p-1.5 text-text-muted max-w-xs truncate" title={f.input_observation_ids?.join(', ')}>
                          {f.input_observation_ids?.join(', ') || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
