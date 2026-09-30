import React, { useMemo } from 'react';
import type { AdaptiveReportResponse, MetricPresentation, SourceNote } from '../model/types';
import { EquityReportContext } from './useEquityReport';
import { fmtPeriod } from '@/shared/lib/formatting';

function humanizeLocator(raw?: string | null): string | null {
  if (!raw) return null;
  const parts = raw.split(';').map((p) => p.trim()).filter(Boolean);
  const kv: Record<string, string> = {};
  for (const part of parts) {
    const idx = part.indexOf(':');
    if (idx !== -1) {
      kv[part.slice(0, idx).trim()] = part.slice(idx + 1).trim();
    }
  }
  const tokens: string[] = [];
  if (kv.printed_page) {
    tokens.push(`tr. ${kv.printed_page}`);
  } else if (kv.printed_pages) {
    const p = kv.printed_pages.replace(/_and_/g, ', ').split(',').map((s) => s.trim()).join(', ');
    tokens.push(`tr. ${p}`);
  } else if (kv.pdf_pages || kv.pdf_page) {
    tokens.push(`tr. ${(kv.pdf_pages || kv.pdf_page).replace(/_and_/g, ', ')}`);
  } else if (kv.page) {
    tokens.push(`tr. ${kv.page}`);
  }

  const sec = kv.section || kv.sections || kv.statement;
  if (sec) {
    let clean = sec.replace(/_/g, ' ');
    if (clean.includes('|')) {
      clean = clean.split('|').map((s) => s.trim()).join(' · ');
    }
    tokens.push(clean);
  } else if (kv.row) {
    tokens.push(kv.row.replace(/_/g, ' '));
  }

  return tokens.length > 0 ? tokens.join(' · ') : raw;
}

export const EquityReportProvider: React.FC<{
  report: AdaptiveReportResponse;
  metrics?: MetricPresentation[];
  children: React.ReactNode;
}> = ({ report, metrics = [], children }) => {
  const facts = useMemo(() => report.facts || [], [report.facts]);
  const datasets = useMemo(() => report.datasets || [], [report.datasets]);

  // Derive highlight entities
  const highlight = useMemo(() => {
    const fromDatasets = datasets.flatMap((d) => d.highlight_entity_ids || []);
    if (fromDatasets.length > 0) return Array.from(new Set(fromDatasets));
    const targetTicker = (report as { target_ticker?: string }).target_ticker;
    if (targetTicker) return [targetTicker];
    return [];
  }, [datasets, report]);

  // Intelligent source notes resolution:
  // 1. Collect cited fact_ids in document order from blocks
  // 2. If report.source_notes is present, re-index them in document order (1, 2, 3...)
  // 3. If report.source_notes is empty, synthesize them from evidence_trail and facts
  const sourceNotes = useMemo((): SourceNote[] => {
    const citedFactIds: string[] = [];
    const seenFactIds = new Set<string>();

    const walkObj = (obj: unknown) => {
      if (!obj) return;
      if (Array.isArray(obj)) {
        for (const item of obj) walkObj(item);
      } else if (typeof obj === 'object') {
        const record = obj as Record<string, unknown>;
        if (Array.isArray(record.fact_ids) && typeof record.text === 'string') {
          for (const fid of record.fact_ids) {
            if (typeof fid === 'string' && !seenFactIds.has(fid)) {
              seenFactIds.add(fid);
              citedFactIds.push(fid);
            }
          }
        }
        for (const val of Object.values(record)) {
          walkObj(val);
        }
      }
    };
    walkObj(report.report_spec?.blocks);

    if (report.source_notes && report.source_notes.length > 0) {
      const getFirstCitationIndex = (note: SourceNote): number => {
        if (!note.fact_ids || note.fact_ids.length === 0) return 9999;
        let minIdx = 9999;
        for (const fid of note.fact_ids) {
          const idx = citedFactIds.indexOf(fid);
          if (idx !== -1 && idx < minIdx) {
            minIdx = idx;
          }
        }
        return minIdx;
      };

      const sorted = [...report.source_notes].sort((a, b) => {
        const idxA = getFirstCitationIndex(a);
        const idxB = getFirstCitationIndex(b);
        if (idxA !== idxB) return idxA - idxB;
        return a.note_no - b.note_no;
      });

      return sorted.map((note, i) => ({
        ...note,
        note_no: i + 1
      }));
    }

    // Synthesize source notes from evidence_trail and facts
    const evidenceTrail = (report.evidence_trail || []) as Array<Record<string, unknown>>;
    const factsList = report.facts || [];

    if (evidenceTrail.length === 0 && factsList.length === 0) {
      return [];
    }

    const obsMap = new Map<string, Record<string, unknown>>();
    for (const ev of evidenceTrail) {
      if (typeof ev.observation_id === 'string') {
        obsMap.set(ev.observation_id, ev);
      }
    }

    const factMap = new Map<string, (typeof factsList)[0]>();
    for (const f of factsList) {
      factMap.set(f.fact_id, f);
    }

    const allFactIds = [...citedFactIds];
    for (const f of factsList) {
      if (!seenFactIds.has(f.fact_id)) {
        seenFactIds.add(f.fact_id);
        allFactIds.push(f.fact_id);
      }
    }

    const sourceMap = new Map<string, SourceNote>();
    const orderedKeys: string[] = [];

    for (const fid of allFactIds) {
      const fact = factMap.get(fid);
      if (!fact) continue;
      for (const obsId of fact.input_observation_ids || []) {
        let ev = obsMap.get(obsId);
        if (!ev) {
          for (const [k, v] of obsMap.entries()) {
            if (obsId.includes(k) || k.includes(obsId)) {
              ev = v;
              break;
            }
          }
        }
        if (!ev) continue;

        const srcKey =
          (typeof ev.source_id === 'string' && ev.source_id) ||
          (typeof ev.source_url === 'string' && ev.source_url) ||
          obsId;

        if (!sourceMap.has(srcKey)) {
          const ticker = (typeof ev.ticker === 'string' && ev.ticker) || fact.entity_id || '';
          const periodStr = fmtPeriod((typeof ev.period === 'string' && ev.period) || fact.period);
          const isConsolidated =
            (typeof ev.source_id === 'string' && ev.source_id.toLowerCase().includes('consolidated')) ||
            obsId.toLowerCase().includes('consolidated');
          const scope = isConsolidated ? 'hợp nhất' : '';
          const title = `${ticker} · BCTC ${scope} ${periodStr}`.replace(/\s+/g, ' ').trim();
          const locator = humanizeLocator(typeof ev.table_locator === 'string' ? ev.table_locator : null);
          const url =
            (typeof ev.source_url === 'string' && ev.source_url) ||
            (typeof ev.source_doc === 'string' && ev.source_doc) ||
            null;

          sourceMap.set(srcKey, {
            note_no: 0,
            source_id: (typeof ev.source_id === 'string' && ev.source_id) || srcKey,
            title,
            url,
            locator,
            fact_ids: []
          });
          orderedKeys.push(srcKey);
        }

        const note = sourceMap.get(srcKey)!;
        if (!note.fact_ids?.includes(fid)) {
          note.fact_ids?.push(fid);
        }
      }
    }

    return orderedKeys.map((key, idx) => ({
      ...sourceMap.get(key)!,
      note_no: idx + 1
    }));
  }, [report]);

  const getNoteNumbersForFactIds = useMemo(() => {
    return (factIds: string[]): number[] => {
      if (!factIds || factIds.length === 0 || sourceNotes.length === 0) return [];
      const set = new Set<number>();
      for (const fId of factIds) {
        for (const note of sourceNotes) {
          if (note.fact_ids && note.fact_ids.includes(fId)) {
            set.add(note.note_no);
          }
        }
      }
      return Array.from(set).sort((a, b) => a - b);
    };
  }, [sourceNotes]);

  const value = useMemo(
    () => ({
      report,
      sourceNotes,
      facts,
      datasets,
      metrics,
      highlight,
      getNoteNumbersForFactIds
    }),
    [report, sourceNotes, facts, datasets, metrics, highlight, getNoteNumbersForFactIds]
  );

  return <EquityReportContext.Provider value={value}>{children}</EquityReportContext.Provider>;
};
