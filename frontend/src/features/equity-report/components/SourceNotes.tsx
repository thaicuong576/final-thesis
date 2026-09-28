import React from 'react';
import { useEquityReport } from './useEquityReport';

export const SourceNotes: React.FC = () => {
  const { report, sourceNotes, datasets } = useEquityReport();

  // Determine peer group count
  const allEntities = new Set<string>();
  for (const ds of datasets) {
    for (const r of ds.rows || []) {
      if (r.entity_id) allEntities.add(r.entity_id);
    }
  }
  const isPeerComparison = allEntities.size > 1;
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
                  {note.title}
                </a>
              ) : (
                <span className="font-medium text-text-primary">{note.title}</span>
              )}
              {note.locator && <span> · {note.locator}</span>}
            </div>
          ))}
        </div>
      )}

      {/* Standard Disclaimers */}
      <div className="space-y-0.5 text-text-muted">
        <div>
          Số liệu do code tính từ BCTC gốc, agent chỉ diễn giải.
          {isPeerComparison && ` Mẫu ${peerCount} ngân hàng, không đại diện toàn ngành.`} Không phải khuyến nghị đầu tư.
        </div>
        {limitations.length > 0 && (
          <div className="mt-1">
            {limitations.map((lim, idx) => (
              <div key={idx}>· {lim}</div>
            ))}
          </div>
        )}
      </div>
    </footer>
  );
};
