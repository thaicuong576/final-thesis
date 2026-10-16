import { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Edit2,
  Check,
  X,
  FileImage,
  Layers,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { formatDecimalVi, formatPeriodCode } from '@/shared/lib/formatting';
import { scrubUserText } from '../lib/scrubText';
import type { Row, RowAlternative } from '../model/types';
import { METRIC_IDS, METRIC_LABELS } from '../model/types';

interface ExtractedRowsTableProps {
  rows: Row[];
  onUpdateRow: (rowId: string, value: string | null, confirmed: boolean) => Promise<void>;
  onSelectPage: (page: number) => void;
  selectedPage: number | null;
  highlightedRowIds?: string[];
}

function sourceLabel(src: Row['source']): string {
  switch (src) {
    case 'text_layer':
      return 'Chữ sẵn';
    case 'ocr':
      return 'OCR';
    case 'llamaparse':
      return 'LlamaParse';
    case 'user':
      return 'Tự nhập';
    default:
      return 'Chưa rõ';
  }
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

  // Group rows by metric_id
  const rowsByMetric = METRIC_IDS.map((metricId) => {
    const targetRow = rows.find((r) => r.metric_id === metricId && r.period_role === 'target');
    const priorRow = rows.find((r) => r.metric_id === metricId && r.period_role === 'prior');
    return {
      metricId,
      label: METRIC_LABELS[metricId] || metricId,
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
    // Confirm all rows that have value and no error issues
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

  return (
    <div className="space-y-3" data-testid="extracted-rows-section">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-line pb-2.5">
        <div>
          <h3 className="text-sm font-bold text-ink">Bảng số liệu trích xuất (10 chỉ tiêu đầu vào)</h3>
          <p className="text-xs text-ink-secondary">
            Đơn vị: tỷ đồng (billion VND). Đã xác nhận: {totalConfirmed}/{rows.length} ô.
          </p>
        </div>

        {cleanUnconfirmedCount > 0 && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleConfirmAllClean}
            className="h-8 border-ready/50 bg-ready-soft/40 hover:bg-ready-soft text-text-success text-xs font-semibold self-start sm:self-auto shrink-0"
          >
            <CheckCircle2 className="size-3.5 mr-1" />
            Xác nhận {cleanUnconfirmedCount} ô đã khớp kiểm tra
          </Button>
        )}
      </div>

      {/* Desktop Table View */}
      <div className="hidden md:block overflow-x-auto rounded border border-line bg-card shadow-tactile">
        <table className="w-full border-collapse text-left text-xs" data-testid="extracted-rows-table">
          <thead>
            <tr className="border-b border-line bg-surface-secondary text-ink-secondary">
              <th className="py-2.5 px-3 font-semibold w-1/3">Chỉ tiêu đầu vào</th>
              <th className="py-2.5 px-3 font-semibold text-center w-1/3">
                Kỳ mục tiêu ({formatPeriodCode(rows[0]?.period_id) || 'Kỳ này'})
              </th>
              <th className="py-2.5 px-3 font-semibold text-center w-1/3">
                Kỳ so sánh ({formatPeriodCode(rows.find((r) => r.period_role === 'prior')?.period_id) || 'Kỳ trước'})
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rowsByMetric.map(({ metricId, label, targetRow, priorRow }) => {
              return (
                <tr key={metricId} className="hover:bg-surface-hover/30 transition-colors">
                  <td className="py-2.5 px-3 align-top">
                    <span className="font-semibold text-ink block">{label}</span>
                  </td>

                  {/* Target Cell */}
                  <td className="py-2 px-3 align-top">
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
                      <span className="text-ink-tertiary">—</span>
                    )}
                  </td>

                  {/* Prior Cell */}
                  <td className="py-2 px-3 align-top">
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
                      <span className="text-ink-tertiary">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View (390px friendly) */}
      <div className="md:hidden space-y-3" data-testid="extracted-rows-mobile">
        {rowsByMetric.map(({ metricId, label, targetRow, priorRow }) => (
          <div
            key={metricId}
            className="rounded-md border border-line bg-card p-3 shadow-tactile space-y-2.5"
          >
            <div className="border-b border-line pb-1.5">
              <span className="font-bold text-xs text-ink">{label}</span>
            </div>

            <div className="space-y-2">
              {targetRow && (
                <div className="rounded bg-surface-secondary/50 p-2">
                  <div className="text-[11px] font-semibold text-ink-secondary mb-1">
                    Kỳ này ({formatPeriodCode(targetRow.period_id)}):
                  </div>
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
              )}

              {priorRow && (
                <div className="rounded bg-surface-secondary/50 p-2">
                  <div className="text-[11px] font-semibold text-ink-secondary mb-1">
                    Kỳ trước ({formatPeriodCode(priorRow.period_id)}):
                  </div>
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
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// Subcomponent: Cell / Card Content for a single Row (target or prior)
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
      className={`rounded p-1.5 transition-all space-y-1.5 ${
        isHighlighted
          ? 'ring-2 ring-amber bg-amber-soft/40'
          : row.confirmed
          ? 'bg-ready-soft/20'
          : isNeedsReview
          ? 'bg-warning-soft/30'
          : isMissing
          ? 'bg-blocked-soft/30'
          : ''
      }`}
      data-testid={`row-cell-${row.row_id}`}
    >
      {/* Top Line: Checkbox + Value display / Edit box */}
      <div className="flex items-center justify-between gap-1.5">
        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={row.confirmed}
            disabled={isMissing}
            onChange={onToggleConfirm}
            className="size-3.5 rounded border-line text-ready focus:ring-ready/40 cursor-pointer disabled:opacity-40"
            aria-label={`Xác nhận ${row.label_vi} ${formatPeriodCode(row.period_id)}`}
          />
          <span
            className={`font-mono text-xs font-semibold ${
              isMissing ? 'text-blocked italic' : 'text-ink'
            }`}
          >
            {isMissing ? 'Thiếu giá trị' : formatDecimalVi(row.value_billion_vnd, 3)}
          </span>
        </label>

        {/* Edit button */}
        {!isEditing && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onStartEdit}
            className="h-6 w-6 p-0 text-ink-secondary hover:text-ink shrink-0"
            title="Sửa giá trị ô này"
            aria-label={`Sửa giá trị ${row.row_id}`}
          >
            <Edit2 className="size-3" />
          </Button>
        )}
      </div>

      {/* Editing Form */}
      {isEditing && (
        <div className="flex items-center gap-1 pt-1">
          <Input
            type="text"
            value={editValue}
            onChange={(e) => onEditValueChange(e.target.value)}
            placeholder="Ví dụ: 764.791"
            className="h-7 text-xs font-mono py-0 px-1.5 w-full bg-white"
            autoFocus
            aria-label="Nhập số tiền tỷ đồng"
          />
          <Button
            type="button"
            size="sm"
            disabled={isSaving}
            onClick={onSaveEdit}
            className="h-7 px-2 text-xs bg-amber border border-amber-border hover:bg-amber-hover text-ink shrink-0"
            title="Lưu"
          >
            <Check className="size-3" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onCancelEdit}
            className="h-7 px-1.5 text-xs text-ink-secondary shrink-0"
            title="Hủy"
          >
            <X className="size-3" />
          </Button>
        </div>
      )}

      {/* Secondary info: Edited tag & Original value comparison */}
      {row.edited && row.extracted_value_billion_vnd && (
        <div className="flex items-center gap-1 text-[11px] text-ink-secondary bg-surface-secondary/80 rounded px-1.5 py-0.5">
          <span className="font-semibold text-text-accent">Đã sửa</span>
          <span className="text-ink-tertiary">
            (gốc: {formatDecimalVi(row.extracted_value_billion_vnd, 3)})
          </span>
        </div>
      )}

      {/* Bottom bar: Page source + Source kind + Issues badge */}
      <div className="flex flex-wrap items-center justify-between gap-1 text-[11px] text-ink-secondary pt-0.5">
        <div className="flex items-center gap-1.5">
          {row.page ? (
            <button
              type="button"
              onClick={() => onSelectPage(row.page!)}
              className={`inline-flex items-center gap-0.5 rounded px-1 py-0.2 font-mono text-[10px] font-semibold border transition-colors cursor-pointer ${
                isSelectedPage
                  ? 'bg-amber text-ink border-amber-border'
                  : 'bg-surface-secondary text-text-accent hover:bg-surface-hover border-line'
              }`}
              title={`Xem trang ${row.page}`}
            >
              <FileImage className="size-2.5" />
              <span>Tr. {row.page}</span>
            </button>
          ) : (
            <span className="text-ink-tertiary text-[10px]">Chưa có trang</span>
          )}

          <span className="inline-flex items-center rounded bg-surface-secondary px-1 py-0.2 text-[10px] font-medium text-ink-secondary border border-line">
            {sourceLabel(row.source)}
          </span>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-1">
          {row.confirmed ? (
            <span className="inline-flex items-center gap-0.5 text-ready text-[10px] font-semibold">
              <CheckCircle2 className="size-3" />
              Đã duyệt
            </span>
          ) : isNeedsReview ? (
            <span className="inline-flex items-center gap-0.5 text-warning text-[10px] font-semibold">
              <AlertTriangle className="size-3" />
              Cần xem lại
            </span>
          ) : isMissing ? (
            <span className="inline-flex items-center gap-0.5 text-blocked text-[10px] font-semibold">
              <HelpCircle className="size-3" />
              Thiếu
            </span>
          ) : null}
        </div>
      </div>

      {/* Alternatives Menu if available */}
      {row.alternatives && row.alternatives.length > 0 && (
        <div className="pt-1">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onToggleAltMenu}
            className="h-6 w-full text-[10px] justify-between border-dashed border-border-strong px-1.5 py-0 text-text-accent hover:bg-surface-hover"
          >
            <span className="flex items-center gap-1">
              <Layers className="size-2.5" />
              Chọn số khác ({row.alternatives.length} gợi ý)
            </span>
            <ChevronDown className={`size-2.5 transition-transform ${isAltOpen ? 'rotate-180' : ''}`} />
          </Button>

          {isAltOpen && (
            <div className="mt-1 rounded border border-line bg-card p-1 shadow-tactile space-y-1">
              {row.alternatives.map((alt, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onSelectAlternative(alt)}
                  className="w-full text-left rounded p-1 text-[11px] hover:bg-surface-hover flex items-center justify-between transition-colors cursor-pointer"
                >
                  <div>
                    <span className="font-mono font-bold text-ink">
                      {formatDecimalVi(alt.value_billion_vnd, 3)}
                    </span>
                    <span className="block text-[10px] text-ink-secondary truncate max-w-[180px]">
                      {alt.row_label} (Tr. {alt.page})
                    </span>
                  </div>
                  <span className="text-[10px] text-text-accent font-semibold">Chọn</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Row Issues */}
      {row.issues && row.issues.length > 0 && (
        <div className="space-y-0.5 pt-0.5">
          {row.issues.map((iss, i) => (
            <div
              key={i}
              className={`rounded px-1.5 py-0.5 text-[10px] leading-tight ${
                iss.severity === 'error'
                  ? 'bg-blocked-soft text-blocked font-medium'
                  : 'bg-warning-soft text-text-warning'
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
