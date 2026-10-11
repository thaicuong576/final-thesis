import React, { useState, useMemo, useEffect } from 'react';
import { Info, ChevronDown, ChevronUp } from 'lucide-react';
import { useEquityReport } from './useEquityReport';
import { cleanReaderLimitations, formatDisplayText, humanizeLocator } from '@/shared/lib/formatting';
import type { SourceNote } from '../model/types';

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

interface FilingGroup {
  filingTitle: string;
  url?: string | null;
  notes: SourceNote[];
}

export const SourceNotes: React.FC = () => {
  const { report, sourceNotes, datasets, onOpenSource } = useEquityReport();
  const [isExpanded, setIsExpanded] = useState(
    () => typeof window !== 'undefined' && Boolean(window.location.hash?.startsWith('#note-'))
  );

  // Auto-expand if user navigates to an anchor hash (e.g. #note-1)
  useEffect(() => {
    const handleHash = () => {
      if (typeof window !== 'undefined' && window.location.hash.startsWith('#note-')) {
        setIsExpanded(true);
      }
    };
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

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

  // Group notes by bank filing (one line per bank filing)
  const filingGroups = useMemo<FilingGroup[]>(() => {
    if (!sourceNotes || sourceNotes.length === 0) return [];
    const map = new Map<string, FilingGroup>();
    for (const note of sourceNotes) {
      const key = (note.title || 'Báo cáo tài chính').trim();
      const existing = map.get(key);
      if (existing) {
        existing.notes.push(note);
        if (!existing.url && note.url) existing.url = note.url;
      } else {
        map.set(key, {
          filingTitle: key,
          url: note.url,
          notes: [note]
        });
      }
    }
    return Array.from(map.values());
  }, [sourceNotes]);

  return (
    <footer className="mt-6 pt-5 border-t border-border-subtle font-sans">
      {sourceNotes && sourceNotes.length > 0 && (
        <section id="source-notes" aria-label="Nguồn số liệu" className="scroll-mt-20">
          <div className="flex items-center justify-between mb-2">
            <h2 id="sources" className="text-[13px] font-semibold text-text-primary m-0">
              <button
                type="button"
                onClick={() => setIsExpanded((prev) => !prev)}
                className="text-left font-semibold text-text-primary hover:text-text-accent cursor-pointer bg-transparent border-none p-0 inline-flex items-center gap-1.5 transition-colors"
                aria-expanded={isExpanded}
              >
                <span>
                  Nguồn: {filingGroups.length} báo cáo tài chính, {sourceNotes.length} số liệu — {isExpanded ? 'thu gọn' : 'xem'}
                </span>
                {isExpanded ? (
                  <ChevronUp className="size-4 text-text-tertiary shrink-0" aria-hidden="true" />
                ) : (
                  <ChevronDown className="size-4 text-text-tertiary shrink-0" aria-hidden="true" />
                )}
              </button>
            </h2>
          </div>

          <ol
            className={
              isExpanded
                ? 'mt-3 space-y-2.5 text-[12.5px] leading-relaxed text-text-secondary list-none p-0 m-0 divide-y divide-border-subtle/60'
                : 'hidden'
            }
          >
            {filingGroups.map((group, gIdx) => (
              <li
                key={group.filingTitle || gIdx}
                className={`pt-2 flex flex-col sm:flex-row sm:items-baseline gap-1.5 ${gIdx === 0 ? 'pt-0' : ''}`}
              >
                <div className="shrink-0 font-medium text-text-primary">
                  {group.url ? (
                    <a
                      href={group.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline decoration-border-default underline-offset-2 hover:decoration-text-primary"
                    >
                      {formatDisplayText(group.filingTitle)}
                    </a>
                  ) : (
                    formatDisplayText(group.filingTitle)
                  )}
                  <span className="text-text-tertiary font-normal"> · </span>
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  {group.notes.map((note) => {
                    const displayLocator = humanizeLocator(note.locator);
                    return (
                      <span
                        id={`note-${note.note_no}`}
                        key={note.note_no}
                        className="scroll-mt-24 inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-secondary text-[11.5px] border border-border-subtle text-text-secondary"
                      >
                        <a
                          href={`#note-${note.note_no}`}
                          onClick={(e) => {
                            if (onOpenSource) {
                              e.preventDefault();
                              onOpenSource(note.note_no);
                            }
                          }}
                          className="text-text-accent font-semibold hover:underline font-mono"
                          title={`Số liệu #${note.note_no}`}
                        >
                          #{note.note_no}
                        </a>
                        {displayLocator && (
                          <span className="text-text-secondary">{formatDisplayText(displayLocator)}</span>
                        )}
                      </span>
                    );
                  })}
                </div>
              </li>
            ))}
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
