import React from 'react';
import { useEquityReport } from './useEquityReport';
import { formatDisplayText } from '@/shared/lib/formatting';

export const SourceNotes: React.FC = () => {
  const { report, sourceNotes, datasets } = useEquityReport();

  // Determine peer group count
  const allEntities = new Set<string>();
  for (const ds of datasets) {
    for (const r of ds.rows || []) {
      if (r.entity_id) allEntities.add(r.entity_id);
    }
  }
  const qType = report.question_type;
  const showSampleDisclaimer = (qType === 'company_profile' || qType === 'ranking') && allEntities.size >= 3;
  const peerCount = allEntities.size || 5;

  const limitations = (report.limitations as string[] | undefined) || [];

  return (
    <footer className="border-t border-line mt-6 pt-3 text-[11px] leading-[1.8] text-text-muted font-sans">
      {/* Source Notes List */}
      {sourceNotes && sourceNotes.length > 0 && (
        <div className="space-y-1 mb-3">
          {sourceNotes.map((note) => (
            <div id={`note-${note.note_no}`} key={note.note_no} className="scroll-mt-4">
              <span>{note.note_no} · </span>
              {note.url ? (
                <a
                  href={note.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-text-primary hover:underline font-medium"
                >
                  {formatDisplayText(note.title)}
                </a>
              ) : (
                <span className="font-medium text-text-primary">{formatDisplayText(note.title)}</span>
              )}
              {note.locator && <span> · {formatDisplayText(note.locator)}</span>}
            </div>
          ))}
        </div>
      )}

      {/* Standard Disclaimers */}
      <div className="space-y-0.5 text-text-muted">
        <div>
          Số liệu do code tính từ BCTC gốc, agent chỉ diễn giải.
          {showSampleDisclaimer && ` Mẫu ${peerCount} ngân hàng, không đại diện toàn ngành.`} Không phải khuyến nghị đầu tư.
        </div>
        {limitations.length > 0 && (
          <div className="mt-2.5 pt-2 border-t border-line/60">
            <div className="font-semibold text-text-secondary mb-1">
              Giới hạn phạm vi &amp; dữ liệu:
            </div>
            <ul className="space-y-1 list-none pl-0">
              {limitations.map((lim, idx) => (
                <li key={idx} className="flex items-start gap-1.5 leading-relaxed">
                  <span className="text-text-muted shrink-0">·</span>
                  <span>{formatDisplayText(lim)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </footer>
  );
};
