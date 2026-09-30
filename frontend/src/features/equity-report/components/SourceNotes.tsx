import React from 'react';
import { Info } from 'lucide-react';
import { useEquityReport } from './useEquityReport';
import { cleanReaderLimitations, formatDisplayText, humanizeLocator } from '@/shared/lib/formatting';

// Runtime limitation strings that describe provenance mechanics rather than the answer itself.
const PLAIN_LIMITATIONS: Array<[RegExp, string]> = [
  [
    /không có đoạn trích tài liệu đã duyệt/i,
    'Số liệu được đối chiếu tới trang cụ thể của BCTC gốc; báo cáo chưa kèm đoạn trích nguyên văn.'
  ]
];

function plainLimitation(text: string): string {
  for (const [pattern, plain] of PLAIN_LIMITATIONS) {
    if (pattern.test(text)) return plain;
  }
  return text;
}

export const SourceNotes: React.FC = () => {
  const { report, sourceNotes, datasets } = useEquityReport();

  const allEntities = new Set<string>();
  for (const ds of datasets) {
    for (const r of ds.rows || []) {
      if (r.entity_id) allEntities.add(r.entity_id);
    }
  }
  const qType = report.question_type;
  const showSampleDisclaimer = (qType === 'company_profile' || qType === 'ranking') && allEntities.size >= 3;
  const peerCount = allEntities.size || 5;

  const limitations = Array.from(
    new Set(cleanReaderLimitations((report.limitations as string[] | undefined) || []).map(plainLimitation))
  );

  return (
    <footer className="mt-6 pt-5 border-t border-border-subtle font-sans">
      {sourceNotes && sourceNotes.length > 0 && (
        <section aria-label="Nguồn số liệu">
          <h2 className="text-[13px] font-semibold text-text-primary mb-2">Nguồn</h2>
          <ol className="space-y-1.5 text-[12.5px] leading-relaxed text-text-secondary list-none p-0 m-0">
            {sourceNotes.map((note) => {
              const displayLocator = humanizeLocator(note.locator);
              return (
                <li id={`note-${note.note_no}`} key={note.note_no} className="scroll-mt-20 flex gap-2">
                  <span className="shrink-0 w-4 text-right tabular-nums text-text-tertiary">{note.note_no}</span>
                  <span className="min-w-0">
                    {note.url ? (
                      <a
                        href={note.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-text-primary font-medium underline decoration-border-default underline-offset-2 hover:decoration-text-primary"
                      >
                        {formatDisplayText(note.title)}
                      </a>
                    ) : (
                      <span className="font-medium text-text-primary">{formatDisplayText(note.title)}</span>
                    )}
                    {displayLocator && (
                      <span title={note.locator || undefined}> · {formatDisplayText(displayLocator)}</span>
                    )}
                  </span>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {limitations.length > 0 && (
        <section
          aria-label="Giới hạn dữ liệu"
          className="mt-5 rounded-lg bg-surface-secondary border border-border-subtle px-4 py-3"
        >
          <h2 className="flex items-center gap-1.5 text-[13px] font-semibold text-text-primary mb-1.5">
            <Info className="size-3.5 text-text-secondary" aria-hidden="true" />
            Giới hạn dữ liệu
          </h2>
          <ul className="space-y-1 text-[12.5px] leading-relaxed text-text-secondary list-disc pl-5 m-0 marker:text-text-tertiary">
            {limitations.map((lim, idx) => (
              <li key={idx}>{formatDisplayText(lim)}</li>
            ))}
          </ul>
        </section>
      )}

      <p className="mt-4 mb-0 text-[12px] leading-relaxed text-text-tertiary">
        Số liệu do chương trình tính từ BCTC gốc; mô hình ngôn ngữ chỉ diễn giải.
        {showSampleDisclaimer && ` Mẫu ${peerCount} ngân hàng, không đại diện toàn ngành.`} Không phải khuyến nghị đầu tư.
      </p>
    </footer>
  );
};
