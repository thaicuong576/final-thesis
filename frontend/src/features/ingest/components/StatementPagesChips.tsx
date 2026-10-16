import { FileText, CheckCircle2 } from 'lucide-react';
import type { StatementPages } from '../model/types';

interface StatementPagesChipsProps {
  pages: StatementPages;
  selectedPage: number | null;
  onSelectPage: (page: number) => void;
}

interface StatementGroup {
  id: keyof StatementPages;
  label: string;
  pages: number[];
}

export function StatementPagesChips({
  pages,
  selectedPage,
  onSelectPage,
}: StatementPagesChipsProps) {
  const groups: StatementGroup[] = [
    {
      id: 'balance_sheet',
      label: 'Bảng cân đối kế toán',
      pages: pages.balance_sheet || [],
    },
    {
      id: 'income_statement',
      label: 'Kết quả kinh doanh',
      pages: pages.income_statement || [],
    },
    {
      id: 'loan_quality_note',
      label: 'Thuyết minh chất lượng nợ',
      pages: pages.loan_quality_note || [],
    },
  ];

  const totalPagesFound = groups.reduce((acc, g) => acc + g.pages.length, 0);

  return (
    <div className="rounded-md border border-line bg-surface-secondary/40 p-3.5 space-y-2.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="size-4 text-text-accent" aria-hidden="true" />
          <span className="text-xs font-bold text-ink">
            Các trang báo cáo nhận diện được ({totalPagesFound} trang)
          </span>
        </div>
        <span className="text-[11px] text-ink-secondary">
          Bấm vào trang để xem ảnh gốc
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {groups.map((group) => {
          const hasPages = group.pages.length > 0;
          return (
            <div
              key={group.id}
              className="inline-flex items-center gap-1.5 rounded-md border border-line bg-card px-2.5 py-1 text-xs shadow-tactile"
            >
              <CheckCircle2
                className={`size-3.5 ${hasPages ? 'text-ready' : 'text-ink-tertiary'}`}
                aria-hidden="true"
              />
              <span className="font-semibold text-ink">{group.label}:</span>
              {hasPages ? (
                <div className="inline-flex items-center gap-1">
                  {group.pages.map((p) => {
                    const isSelected = selectedPage === p;
                    return (
                      <button
                        key={p}
                        type="button"
                        onClick={() => onSelectPage(p)}
                        className={`rounded px-1.5 py-0.5 font-mono text-[11px] font-semibold transition-colors cursor-pointer ${
                          isSelected
                            ? 'bg-amber text-ink border border-amber-border'
                            : 'bg-surface-secondary text-text-accent hover:bg-surface-hover border border-line'
                        }`}
                        title={`Xem ảnh trang ${p}`}
                        aria-pressed={isSelected}
                      >
                        Tr. {p}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <span className="text-ink-tertiary italic">Chưa tìm thấy</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
