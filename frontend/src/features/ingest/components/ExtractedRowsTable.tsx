import { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Edit2,
  Check,
  X,
  Layers,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { formatDecimalVi, formatPeriodCode } from '@/shared/lib/formatting';
import type { Row, RowAlternative } from '../model/types';
import { METRIC_IDS, METRIC_LABELS } from '../model/types';
import { scrubUserText } from '../lib/scrubText';

interface ExtractedRowsTableProps {
  rows: Row[];
  onUpdateRow: (rowId: string, value: string | null, confirmed: boolean) => Promise<void>;
  onSelectPage: (page: number) => void;
  selectedPage: number | null;
  highlightedRowIds?: string[];
}

export function ExtractedRowsTable({
  rows,
  onUpdateRow,
  onSelectPage,
  selectedPage,
  highlightedRowIds = [],
}: ExtractedRowsTableProps) {
  const [editingRowId, setEditingRowId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [openAltMenuRowId, setOpenAltMenuRowId] = useState<string | null>(null);

  // Collect all unique metric IDs present in the rows while preserving METRIC_IDS order
  const presentMetricIds = Array.from(
    new Set([...METRIC_IDS, ...rows.map((r) => r.metric_id)])
  ).filter((m) => rows.some((r) => r.metric_id === m));

  const rowsByMetric = presentMetricIds.map((metricId) => {
    const targetRow = rows.find((r) => r.metric_id === metricId && r.period_role === 'target');
    const priorRow = rows.find((r) => r.metric_id === metricId && r.period_role === 'prior');
    const metricLabel =
      METRIC_LABELS[metricId as keyof typeof METRIC_LABELS] ||
      targetRow?.label_vi ||
      priorRow?.label_vi ||
      metricId;
    return {
      metricId,
      label: metricLabel,
      targetRow,
      priorRow,
    };
  });

  const handleStartEdit = (row: Row) => {
    setEditingRowId(row.row_id);
    setEditValue(row.value_billion_vnd ?? '');
    setOpenAltMenuRowId(null);
  };

  const handleCancelEdit = () => {
    setEditingRowId(null);
    setEditValue('');
  };

  const handleSaveEdit = async (row: Row) => {
    setIsSaving(true);
    try {
      const val = editValue.trim() === '' ? null : editValue.trim();
      await onUpdateRow(row.row_id, val, row.confirmed);
      setEditingRowId(null);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSelectAlternative = async (row: Row, alt: RowAlternative) => {
    setOpenAltMenuRowId(null);
    await onUpdateRow(row.row_id, alt.value_billion_vnd, row.confirmed);
  };

  const handleToggleConfirm = async (row: Row) => {
    await onUpdateRow(row.row_id, row.value_billion_vnd, !row.confirmed);
  };

  const handleConfirmAllClean = async () => {
    const candidates = rows.filter(
      (r) =>
        !r.confirmed &&
        r.value_billion_vnd !== null &&
        !r.issues.some((iss) => iss.severity === 'error')
    );
    for (const r of candidates) {
      await onUpdateRow(r.row_id, r.value_billion_vnd, true);
    }
  };

  const totalConfirmed = rows.filter((r) => r.confirmed).length;
  const cleanUnconfirmedCount = rows.filter(
    (r) =>
      !r.confirmed &&
      r.value_billion_vnd !== null &&
      !r.issues.some((iss) => iss.severity === 'error')
  ).length;

  const targetPeriodLabel = formatPeriodCode(rows.find((r) => r.period_role === 'target')?.period_id) || 'Kỳ này';
  const priorPeriodLabel = formatPeriodCode(rows.find((r) => r.period_role === 'prior')?.period_id) || 'Kỳ trước';

  return (
    <div className="space-y-2.5" data-testid="extracted-rows-section">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1.5 border-b border-line pb-2">
        <div>
          <h3 className="text-sm font-bold text-ink">Bảng số liệu trích xuất (10 chỉ tiêu đầu vào)</h3>
          <p className="text-[11px] text-ink-secondary">
            Nhận diện bằng OCR · Đơn vị: tỷ VND · Đã xác nhận: {totalConfirmed}/{rows.length} ô
          </p>
        </div>

        {cleanUnconfirmedCount > 0 && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleConfirmAllClean}
            className="h-7 border-line text-ink text-xs font-semibold self-start sm:self-auto shrink-0"
          >
            <CheckCircle2 className="size-3 mr-1 text-ready" />
            Xác nhận {cleanUnconfirmedCount} ô đã khớp kiểm tra
          </Button>
        )}
      </div>

      {/* Desktop Table View */}
      <div className="hidden md:block overflow-x-auto rounded border border-line bg-card">
        <table className="w-full border-collapse text-left text-xs" data-testid="extracted-rows-table">
          <thead>
            <tr className="border-b border-line bg-surface-secondary/60 text-ink-secondary">
              <th className="py-2 px-3 font-semibold w-2/5">Chỉ tiêu đầu vào</th>
              <th className="py-2 px-3 font-semibold text-right w-[30%]">
                Kỳ mục tiêu ({targetPeriodLabel})
              </th>
              <th className="py-2 px-3 font-semibold text-right w-[30%]">
                Kỳ so sánh ({priorPeriodLabel})
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rowsByMetric.map(({ metricId, label, targetRow, priorRow }) => {
              return (
                <tr key={metricId} className="hover:bg-surface-secondary/30 transition-colors">
                  <td className="py-2 px-3 align-top">
                    <span className="font-semibold text-ink">{label}</span>
                  </td>

                  {/* Target period cell */}
                  <td className="py-2 px-3 align-top text-right">
                    {targetRow ? (
                      <RowCellContent
                        row={targetRow}
                        isEditing={editingRowId === targetRow.row_id}
                        editValue={editValue}
                        isSaving={isSaving}
                        isHighlighted={highlightedRowIds.includes(targetRow.row_id)}
                        isSelectedPage={selectedPage === targetRow.page}
                        isAltOpen={openAltMenuRowId === targetRow.row_id}
                        onStartEdit={() => handleStartEdit(targetRow)}
                        onCancelEdit={handleCancelEdit}
                        onSaveEdit={() => handleSaveEdit(targetRow)}
                        onEditValueChange={setEditValue}
                        onToggleConfirm={() => handleToggleConfirm(targetRow)}
                        onSelectPage={onSelectPage}
                        onToggleAltMenu={() =>
                          setOpenAltMenuRowId((id) => (id === targetRow.row_id ? null : targetRow.row_id))
                        }
                        onSelectAlternative={(alt) => handleSelectAlternative(targetRow, alt)}
                      />
                    ) : (
                      <span className="text-ink-tertiary font-mono text-[11px]">—</span>
                    )}
                  </td>

                  {/* Prior period cell */}
                  <td className="py-2 px-3 align-top text-right">
                    {priorRow ? (
                      <RowCellContent
                        row={priorRow}
                        isEditing={editingRowId === priorRow.row_id}
                        editValue={editValue}
                        isSaving={isSaving}
                        isHighlighted={highlightedRowIds.includes(priorRow.row_id)}
                        isSelectedPage={selectedPage === priorRow.page}
                        isAltOpen={openAltMenuRowId === priorRow.row_id}
                        onStartEdit={() => handleStartEdit(priorRow)}
                        onCancelEdit={handleCancelEdit}
                        onSaveEdit={() => handleSaveEdit(priorRow)}
                        onEditValueChange={setEditValue}
                        onToggleConfirm={() => handleToggleConfirm(priorRow)}
                        onSelectPage={onSelectPage}
                        onToggleAltMenu={() =>
                          setOpenAltMenuRowId((id) => (id === priorRow.row_id ? null : priorRow.row_id))
                        }
                        onSelectAlternative={(alt) => handleSelectAlternative(priorRow, alt)}
                      />
                    ) : (
                      <span className="text-ink-tertiary font-mono text-[11px]">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Flat List (<= 768px, perfect 390px) */}
      <div className="md:hidden divide-y divide-line rounded border border-line bg-card">
        {rowsByMetric.map(({ metricId, label, targetRow, priorRow }) => (
          <div key={metricId} className="p-3 space-y-2">
            <div className="font-semibold text-xs text-ink">{label}</div>

            {targetRow && (
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="text-ink-secondary text-[11px] shrink-0">
                  {targetPeriodLabel}:
                </span>
                <div className="flex-1 min-w-0">
                  <RowCellContent
                    row={targetRow}
                    isEditing={editingRowId === targetRow.row_id}
                    editValue={editValue}
                    isSaving={isSaving}
                    isHighlighted={highlightedRowIds.includes(targetRow.row_id)}
                    isSelectedPage={selectedPage === targetRow.page}
                    isAltOpen={openAltMenuRowId === targetRow.row_id}
                    onStartEdit={() => handleStartEdit(targetRow)}
                    onCancelEdit={handleCancelEdit}
                    onSaveEdit={() => handleSaveEdit(targetRow)}
                    onEditValueChange={setEditValue}
                    onToggleConfirm={() => handleToggleConfirm(targetRow)}
                    onSelectPage={onSelectPage}
                    onToggleAltMenu={() =>
                      setOpenAltMenuRowId((id) => (id === targetRow.row_id ? null : targetRow.row_id))
                    }
                    onSelectAlternative={(alt) => handleSelectAlternative(targetRow, alt)}
                  />
                </div>
              </div>
            )}

            {priorRow && (
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="text-ink-secondary text-[11px] shrink-0">
                  {priorPeriodLabel}:
                </span>
                <div className="flex-1 min-w-0">
                  <RowCellContent
                    row={priorRow}
                    isEditing={editingRowId === priorRow.row_id}
                    editValue={editValue}
                    isSaving={isSaving}
                    isHighlighted={highlightedRowIds.includes(priorRow.row_id)}
                    isSelectedPage={selectedPage === priorRow.page}
                    isAltOpen={openAltMenuRowId === priorRow.row_id}
                    onStartEdit={() => handleStartEdit(priorRow)}
                    onCancelEdit={handleCancelEdit}
                    onSaveEdit={() => handleSaveEdit(priorRow)}
                    onEditValueChange={setEditValue}
                    onToggleConfirm={() => handleToggleConfirm(priorRow)}
                    onSelectPage={onSelectPage}
                    onToggleAltMenu={() =>
                      setOpenAltMenuRowId((id) => (id === priorRow.row_id ? null : priorRow.row_id))
                    }
                    onSelectAlternative={(alt) => handleSelectAlternative(priorRow, alt)}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// Subcomponent: Clean Cell Content for a single Row (target or prior)
// -------------------------------------------------------------------------
interface RowCellContentProps {
  row: Row;
  isEditing: boolean;
  editValue: string;
  isSaving: boolean;
  isHighlighted: boolean;
  isSelectedPage: boolean;
  isAltOpen: boolean;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
  onEditValueChange: (val: string) => void;
  onToggleConfirm: () => void;
  onSelectPage: (p: number) => void;
  onToggleAltMenu: () => void;
  onSelectAlternative: (alt: RowAlternative) => void;
}

function RowCellContent({
  row,
  isEditing,
  editValue,
  isSaving,
  isHighlighted,
  isSelectedPage,
  isAltOpen,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onEditValueChange,
  onToggleConfirm,
  onSelectPage,
  onToggleAltMenu,
  onSelectAlternative,
}: RowCellContentProps) {
  const isMissing = row.status === 'missing' || row.value_billion_vnd === null;
  const isNeedsReview = row.status === 'needs_review';

  return (
    <div
      className={`rounded px-1.5 py-1 transition-colors ${
        isHighlighted
          ? 'bg-amber-soft/40 ring-1 ring-amber'
          : isMissing
          ? 'bg-blocked-soft/20'
          : isNeedsReview
          ? 'bg-warning-soft/20'
          : ''
      }`}
      data-testid={`row-cell-${row.row_id}`}
    >
      {/* Editing Form */}
      {isEditing ? (
        <div className="flex items-center justify-end gap-1">
          <Input
            type="text"
            value={editValue}
            onChange={(e) => onEditValueChange(e.target.value)}
            placeholder="Ví dụ: 764.791"
            className="h-7 text-xs font-mono py-0 px-1.5 w-28 bg-card text-right"
            autoFocus
            aria-label="Nhập số tiền tỷ đồng"
          />
          <Button
            type="button"
            size="sm"
            disabled={isSaving}
            onClick={onSaveEdit}
            className="h-7 px-1.5 text-xs bg-amber border border-amber-border hover:bg-amber-hover text-ink shrink-0"
            title="Lưu"
          >
            <Check className="size-3" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onCancelEdit}
            className="h-7 px-1 text-xs text-ink-secondary shrink-0"
            title="Hủy"
          >
            <X className="size-3" />
          </Button>
        </div>
      ) : (
        /* Normal Display: Checkbox + Value + Page link + Status mark (ONLY when not OK) + Edit button */
        <div className="flex items-center justify-end gap-1.5">
          {/* Checkbox */}
          <input
            type="checkbox"
            checked={row.confirmed}
            disabled={isMissing}
            onChange={onToggleConfirm}
            className="size-3.5 rounded border-line text-ready focus:ring-ready/40 cursor-pointer disabled:opacity-30 shrink-0"
            aria-label={`Xác nhận ${row.label_vi} ${formatPeriodCode(row.period_id)}`}
          />

          {/* Formatted Number */}
          <span
            className={`font-mono text-xs tabular-nums ${
              isMissing ? 'text-blocked italic' : 'text-ink font-semibold'
            }`}
          >
            {isMissing ? 'Thiếu giá trị' : formatDecimalVi(row.value_billion_vnd, 3)}
          </span>

          {/* Edited indicator */}
          {row.edited && (
            <span
              className="text-[10px] text-text-accent font-semibold"
              title={row.extracted_value_billion_vnd ? `Gốc: ${formatDecimalVi(row.extracted_value_billion_vnd, 3)}` : undefined}
            >
              Đã sửa
            </span>
          )}

          {/* Page Link (small) */}
          {row.page ? (
            <button
              type="button"
              onClick={() => onSelectPage(row.page!)}
              className={`font-mono text-[10px] underline cursor-pointer transition-colors ${
                isSelectedPage ? 'text-ink font-bold' : 'text-text-accent hover:text-ink'
              }`}
              title={`Xem tài liệu trang ${row.page}`}
            >
              tr.{row.page}
            </button>
          ) : null}

          {/* Status Mark ONLY when NOT OK */}
          {isMissing ? (
            <span title="Thiếu giá trị" className="inline-flex text-blocked">
              <HelpCircle className="size-3 text-blocked shrink-0" />
            </span>
          ) : isNeedsReview ? (
            <span title="Cần xem lại" className="inline-flex text-warning">
              <AlertTriangle className="size-3 text-warning shrink-0" />
            </span>
          ) : null}

          {/* Edit Button (subtle, compact) */}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onStartEdit}
            className="h-5 w-5 p-0 text-ink-tertiary hover:text-ink shrink-0"
            title="Sửa giá trị ô này"
            aria-label={`Sửa giá trị ${row.row_id}`}
          >
            <Edit2 className="size-2.5" />
          </Button>
        </div>
      )}

      {/* Alternatives Menu if available */}
      {row.alternatives && row.alternatives.length > 0 && (
        <div className="pt-0.5 text-right">
          <button
            type="button"
            onClick={onToggleAltMenu}
            className="inline-flex items-center gap-0.5 text-[10px] text-text-accent hover:underline cursor-pointer"
          >
            <Layers className="size-2.5" />
            <span>Chọn số khác ({row.alternatives.length})</span>
            <ChevronDown className={`size-2.5 transition-transform ${isAltOpen ? 'rotate-180' : ''}`} />
          </button>

          {isAltOpen && (
            <div className="mt-1 rounded border border-line bg-card p-1 shadow-tactile space-y-1 text-left">
              {row.alternatives.map((alt, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onSelectAlternative(alt)}
                  className="w-full text-left rounded p-1 text-[11px] hover:bg-surface-secondary flex items-center justify-between transition-colors cursor-pointer"
                >
                  <div>
                    <span className="font-mono font-bold text-ink">
                      {formatDecimalVi(alt.value_billion_vnd, 3)}
                    </span>
                    <span className="block text-[10px] text-ink-secondary truncate max-w-[160px]">
                      {alt.row_label} (Tr. {alt.page})
                    </span>
                  </div>
                  <span className="text-[10px] text-text-accent font-semibold ml-2">Chọn</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Row Issues */}
      {row.issues && row.issues.length > 0 && (
        <div className="space-y-0.5 pt-1 text-right">
          {row.issues.map((iss, i) => (
            <div
              key={i}
              className={`text-[10px] leading-tight ${
                iss.severity === 'error' ? 'text-blocked font-medium' : 'text-warning'
              }`}
            >
              {scrubUserText(iss.message_vi)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
