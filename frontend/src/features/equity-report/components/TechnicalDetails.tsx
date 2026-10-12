import React, { useState } from 'react';
import { useEquityReport } from './useEquityReport';
import { formatDisplayText, formatDecimalVi } from '@/shared/lib/formatting';
import { ChevronRight } from 'lucide-react';

const REASON_VI_MAP: Record<string, string> = {
  missing_fact_citation: 'Thiếu trích dẫn số liệu / fact id',
  unknown_fact: 'Số liệu không tồn tại trong danh mục kết quả đã duyệt',
  number_mismatch: 'Số liệu không khớp với dữ liệu nguồn sau làm tròn',
  unit_mismatch: 'Đơn vị tính không khớp loại số liệu được trích dẫn',
  rank_mismatch: 'Thứ hạng không khớp giá trị xếp hạng trong dữ liệu',
  count_mismatch: 'Số lượng mẫu/ngân hàng không khớp danh sách phân tích',
  period_not_cited: 'Kỳ báo cáo không thuộc danh sách các kỳ được trích dẫn',
  entity_not_in_plan: 'Ngân hàng nằm ngoài phạm vi kế hoạch phân tích',
  trend_without_delta: 'Nhận định xu hướng nhưng thiếu số liệu biến động (delta)',
  trend_direction_mismatch: 'Chiều xu hướng không khớp số liệu thực tế',
  comparison_direction_mismatch: 'Chiều so sánh không khớp số liệu thực tế',
  causal_language: 'Chứa từ ngữ quy kết quan hệ nhân quả không có căn cứ',
  investment_advice: 'Chứa khuyến nghị đầu tư (vi phạm chuẩn mực phân tích)',
  unresolved_critique: 'Phản biện chưa được giải quyết thỏa đáng',
};

function getVietnameseReason(reason?: string, reasonCode?: string): string {
  if (reason && reason.trim()) return reason;
  if (reasonCode && REASON_VI_MAP[reasonCode]) return REASON_VI_MAP[reasonCode];
  return 'Không vượt qua kiểm định định mức';
}

export const TechnicalDetails: React.FC = () => {
  const { report, facts } = useEquityReport();
  const [isOpen, setIsOpen] = useState(false);
  const [isDroppedOpen, setIsDroppedOpen] = useState(false);

  const audit = report.narrative_audit;
  const droppedSentences = audit?.sentences_dropped || [];
  const droppedBlocks = audit?.blocks_dropped || [];
  const findings = report.cross_level_findings || [];

  return (
    <div className="mt-4 pt-2 text-xs text-text-muted font-sans print:hidden">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className="text-text-muted hover:text-text-primary font-medium flex items-center gap-1 cursor-pointer bg-transparent border-none p-0"
          aria-expanded={isOpen}
        >
          <ChevronRight className={`size-3.5 transition-transform ${isOpen ? 'rotate-90' : ''}`} aria-hidden="true" />
          <span>Chi tiết kỹ thuật</span>
        </button>

        {droppedSentences.length > 0 && !isOpen && (
          <button
            type="button"
            onClick={() => {
              setIsOpen(true);
              setIsDroppedOpen(true);
            }}
            className="text-amber-800 dark:text-amber-300 hover:underline font-medium text-[11px] bg-amber-500/10 px-2 py-0.5 rounded cursor-pointer border border-amber-600/30"
          >
            Câu bị loại ({droppedSentences.length})
          </button>
        )}
      </div>

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

              {/* Collapsed 'Câu bị loại' panel (Requirement 5) */}
              <div className="mt-3 border border-warning/30 rounded-lg overflow-hidden bg-surface-primary">
                <button
                  type="button"
                  onClick={() => setIsDroppedOpen((prev) => !prev)}
                  className="w-full flex items-center justify-between p-2.5 bg-amber-500/10 hover:bg-amber-500/15 text-amber-900 dark:text-amber-200 font-sans font-semibold text-xs cursor-pointer transition-colors border-none text-left"
                  aria-expanded={isDroppedOpen}
                  aria-controls="panel-dropped-sentences"
                >
                  <span className="flex items-center gap-1.5">
                    <ChevronRight className={`size-3.5 transition-transform ${isDroppedOpen ? 'rotate-90' : ''}`} aria-hidden="true" />
                    <span>Câu bị loại ({droppedSentences.length})</span>
                  </span>
                  <span className="text-[11px] font-normal text-amber-800/80 dark:text-amber-300/80">
                    {isDroppedOpen ? 'Thu gọn' : 'Bấm để mở rộng'}
                  </span>
                </button>

                {isDroppedOpen && (
                  <div id="panel-dropped-sentences" className="p-3 space-y-2 border-t border-warning/30">
                    {droppedSentences.length > 0 ? (
                      droppedSentences.map((s, idx) => (
                        <div key={idx} className="p-2.5 bg-surface-secondary border border-warning/40 rounded text-text-secondary font-sans text-xs">
                          <div className="text-text-primary line-through leading-relaxed">{s.text}</div>
                          <div className="text-text-muted mt-1 text-[11px] flex flex-wrap gap-x-2">
                            <span>
                              Tác giả: {s.author === 'company' ? 'Chuyên viên Doanh nghiệp' : s.author === 'sector' ? 'Chuyên viên Ngành' : s.author || 'Hệ thống'}
                            </span>
                            <span>·</span>
                            <span className="text-amber-800 dark:text-amber-300 font-medium">
                              Lý do: {formatDisplayText(getVietnameseReason(s.reason, s.reason_code))}
                            </span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-text-muted font-sans italic py-1">
                        Không có câu nào bị loại bỏ — toàn bộ các nhận định đều vượt qua kiểm định đối soát số liệu.
                      </div>
                    )}
                  </div>
                )}
              </div>

              {droppedBlocks.length > 0 && (
                <div className="mt-2.5">
                  <div className="text-amber-800 font-semibold mb-1 font-sans">
                    Khối bị bỏ ({droppedBlocks.length}):
                  </div>
                  <div className="space-y-1">
                    {droppedBlocks.map((b, idx) => (
                      <div key={idx} className="p-1.5 bg-surface-primary border border-line rounded">
                        Khối: {formatDisplayText(b.type)} · Lý do: {formatDisplayText(b.reason)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Cross Level Findings */}
          {findings.length > 0 && (
            <div>
              <div className="font-semibold text-text-primary mb-1.5 font-sans text-xs">
                Phát hiện liên tầng (Cross-level Findings: {findings.length})
              </div>
              <div className="space-y-1.5">
                {findings.map((f, idx) => (
                  <div key={idx} className="p-2 bg-surface-primary border border-line rounded text-text-secondary">
                    <div className="font-medium text-text-primary font-sans">{formatDisplayText(f.text)}</div>
                    <div className="text-text-muted mt-0.5">
                      Phân loại: {f.kind === 'counter_trend' ? 'Xu hướng ngược chiều' : f.kind === 'divergent_signals' ? 'Tín hiệu phân hóa' : formatDisplayText(f.kind)}
                      {' · '}Trạng thái: {f.status === 'confirmed' ? 'Đã xác nhận' : f.status}
                    </div>
                  </div>
                ))}
              </div>
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
                        <td className="p-1.5 font-bold text-text-primary">{formatDisplayText(f.fact_id)}</td>
                        <td className="p-1.5">{formatDisplayText(f.metric_id)}</td>
                        <td className="p-1.5 font-medium">{formatDecimalVi(f.value)}</td>
                        <td className="p-1.5 text-text-secondary">{formatDisplayText(f.formula_version)}</td>
                        <td className="p-1.5 text-text-muted max-w-xs truncate" title={f.input_observation_ids?.map((id) => formatDisplayText(id)).join(', ')}>
                          {f.input_observation_ids?.map((id) => formatDisplayText(id)).join(', ') || '—'}
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
