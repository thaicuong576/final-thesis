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
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 text-xs text-ink-secondary py-1">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-semibold text-ink text-[11px]">
          Các trang báo cáo nhận diện được ({totalPagesFound}):
        </span>
        {groups.map((group) => {
          const hasPages = group.pages.length > 0;
          return (
            <div key={group.id} className="inline-flex items-center gap-1 text-[11px]">
              <span className="text-ink-secondary">{group.label}:</span>
              {hasPages ? (
                group.pages.map((p) => {
                  const isSelected = selectedPage === p;
                  return (
                    <button
                      key={p}
                      type="button"
                      onClick={() => onSelectPage(p)}
                      className={`rounded px-1 font-mono text-[11px] font-semibold transition-colors cursor-pointer ${
                        isSelected
                          ? 'bg-amber text-ink'
                          : 'text-text-accent hover:underline'
                      }`}
                      title={`Xem ảnh trang ${p}`}
                      aria-pressed={isSelected}
                    >
                      {p}
                    </button>
                  );
                })
              ) : (
                <span className="text-ink-tertiary italic">chưa thấy</span>
              )}
            </div>
          );
        })}
      </div>
      <span className="text-[11px] text-ink-tertiary hidden sm:inline">
        Nhấn số trang để xem đối chiếu
      </span>
    </div>
  );
}
