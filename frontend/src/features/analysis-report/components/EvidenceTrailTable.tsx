import { useState, useMemo } from 'react';
import { Database, Filter, Hash, Search, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { EvidenceTrailItem } from '../model/types';

interface EvidenceTrailTableProps {
  evidenceTrail: EvidenceTrailItem[];
  selectedEvidenceId?: string | null;
  onClearSelection?: () => void;
}

function isHttpUrl(value?: string | null): value is string {
  if (!value) return false;
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol);
  } catch {
    return false;
  }
}

export function EvidenceTrailTable({
  evidenceTrail,
  selectedEvidenceId,
  onClearSelection
}: EvidenceTrailTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTicker, setFilterTicker] = useState<string>('all');

  const uniqueTickers = useMemo(() => {
    return Array.from(new Set(evidenceTrail.map((e) => e.ticker)));
  }, [evidenceTrail]);

  const filteredItems = useMemo(() => {
    return evidenceTrail.filter((item) => {
      const matchSearch =
        searchTerm === '' ||
        item.evidence_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.metric.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (item.source_doc || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (item.source_url || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (item.table_locator || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (item.provenance_hash || '').toLowerCase().includes(searchTerm.toLowerCase());

      const matchTicker =
        filterTicker === 'all' || item.ticker === filterTicker;

      return matchSearch && matchTicker;
    });
  }, [evidenceTrail, searchTerm, filterTicker]);

  return (
    <section
      id="evidence-trail"
      className="border border-line bg-card rounded-lg p-5 space-y-4 shadow-sm"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line pb-3">
        <div className="flex items-center gap-2">
          <Database className="size-4 text-ink-secondary" aria-hidden="true" />
          <h2 className="text-sm font-bold tracking-tight text-ink">
            Tra cứu bằng chứng và nguồn gốc số liệu
          </h2>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-ink-secondary font-mono bg-surface-secondary px-2 py-0.5 rounded border border-border">
          <span>{evidenceTrail.length} bản ghi API</span>
        </div>
      </div>

      <p className="text-xs text-ink-secondary leading-relaxed">
        Nguồn, vị trí trích xuất và mã đối soát chỉ được hiển thị nếu có trong phản hồi API.
      </p>

      {/* Selected Evidence Highlight Banner */}
      {selectedEvidenceId && (
        <div className="border border-amber-border/60 bg-amber-soft/30 rounded-md p-2.5 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 font-mono">
            <span className="text-ink-secondary">Đang tiêu điểm bằng chứng:</span>
            <span className="font-bold text-ink bg-card px-2 py-0.5 rounded border border-border">
              #{selectedEvidenceId}
            </span>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClearSelection}
            className="h-6 px-2 text-xs text-ink-secondary hover:text-ink gap-1"
          >
            <X className="size-3" aria-hidden="true" />
            <span>Xóa chọn</span>
          </Button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-2.5 text-xs">
        <div className="flex items-center gap-2 flex-1 w-full border border-line rounded-md bg-surface-secondary px-2.5 py-1.5 focus-within:border-border-focus focus-within:bg-card">
          <Search className="size-3.5 text-ink-tertiary shrink-0" aria-hidden="true" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Tìm theo chỉ tiêu, tài liệu, mã bằng chứng, hash..."
            className="w-full bg-transparent border-0 p-0 text-xs text-ink placeholder:text-ink-tertiary focus:outline-none"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              className="text-ink-tertiary hover:text-ink"
              aria-label="Xóa từ khóa tìm kiếm"
            >
              <X className="size-3" aria-hidden="true" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 border border-line rounded-md bg-surface-secondary">
            <Filter className="size-3 text-ink-tertiary" aria-hidden="true" />
            <select
              value={filterTicker}
              onChange={(e) => setFilterTicker(e.target.value)}
              className="bg-transparent border-0 p-0 text-xs font-mono text-ink focus:outline-none"
            >
              <option value="all">Tất cả đơn vị ({evidenceTrail.length})</option>
              {uniqueTickers.map((ticker) => (
                <option key={ticker} value={ticker}>
                  {ticker}
                </option>
              ))}
            </select>
          </div>

          <span className="font-mono text-[11px] text-ink-tertiary">
            {filteredItems.length}/{evidenceTrail.length} bản ghi
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="border border-line rounded-md overflow-x-auto bg-surface-primary">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-line bg-surface-secondary text-[11px] font-mono font-bold uppercase tracking-wider text-ink-secondary">
              <th className="py-2.5 px-3">Mã bằng chứng</th>
              <th className="py-2.5 px-3">Chỉ tiêu</th>
              <th className="py-2.5 px-3">Đơn vị</th>
              <th className="py-2.5 px-3">Chu kỳ</th>
              <th className="py-2.5 px-3 text-right">Giá trị</th>
              <th className="py-2.5 px-3">Tài liệu nguồn</th>
              <th className="py-2.5 px-3">Vị trí trích xuất</th>
              <th className="py-2.5 px-3">Mã Hash đối soát</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {filteredItems.length > 0 ? (
              filteredItems.map((item) => {
                const isSelected = selectedEvidenceId === item.evidence_id;
                return (
                  <tr
                    key={item.evidence_id}
                    className={`transition-colors ${
                      isSelected
                        ? 'bg-amber-soft/30 font-semibold'
                        : 'hover:bg-surface-hover/60'
                    }`}
                  >
                    <td className="py-2.5 px-3 font-mono font-bold text-ink whitespace-nowrap">
                      {item.evidence_id}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-ink whitespace-nowrap font-medium">
                      {item.metric}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-ink whitespace-nowrap">
                      <span className="px-1.5 py-0.5 rounded bg-surface-secondary border border-border text-[11px]">
                        {item.ticker}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-ink-secondary whitespace-nowrap">
                      {item.period}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-right font-bold text-ink whitespace-nowrap">
                      {item.value === null || item.value === undefined
                        ? '—'
                        : typeof item.value === 'number' && !isNaN(item.value)
                        ? item.value.toFixed(2)
                        : String(item.value)}
                    </td>
                    <td className="py-2.5 px-3 text-ink max-w-xs truncate">
                      {isHttpUrl(item.source_url || item.source_doc)
                        ? <a href={item.source_url || item.source_doc || undefined} target="_blank" rel="noreferrer" className="underline underline-offset-2 hover:text-amber-border">{item.source_doc || item.source_url}</a>
                        : item.source_doc || item.source_url || '—'}
                    </td>
                    <td className="py-2.5 px-3 text-ink-secondary max-w-xs truncate">
                      {item.table_locator || '—'}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-ink-tertiary whitespace-nowrap">
                      {item.provenance_hash ? <span className="inline-flex items-center gap-1 bg-surface-secondary px-1.5 py-0.5 rounded border border-border">
                        <Hash className="size-2.5" aria-hidden="true" />
                        <span>{item.provenance_hash}</span>
                      </span> : '—'}
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td
                  colSpan={8}
                  className="py-8 text-center text-xs text-ink-secondary"
                >
                  Không tìm thấy bản ghi bằng chứng phù hợp với điều kiện lọc.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
