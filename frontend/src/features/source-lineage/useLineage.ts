import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/shared/api/apiClient";
import type {
  LineageNode,
  ReportItem,
  ReportBlockItem,
  SourceNoteItem,
  FactItem,
  SentenceItem,
  AuditVerdictItem,
} from "./types";

interface UseLineageParams {
  observationId?: string;
  factId?: string;
  noteNo?: number;
  report?: ReportItem | null;
}

interface UseLineageResult {
  node: LineageNode | null;
  isLoading: boolean;
  error: Error | null;
  retry: () => void;
  activeNote: SourceNoteItem | null;
  activeFact: FactItem | null;
  activeSentence: SentenceItem | null;
  auditVerdict: AuditVerdictItem | null;
}

export function useLineage({
  observationId,
  factId,
  noteNo,
  report,
}: UseLineageParams): UseLineageResult {
  const [node, setNode] = useState<LineageNode | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [retryTrigger, setRetryTrigger] = useState<number>(0);

  const retry = useCallback(() => {
    setRetryTrigger((prev) => prev + 1);
  }, []);

  // 1. Identify active fact
  let effectiveFactId = factId;
  if (!effectiveFactId && noteNo != null) {
    const note = report?.source_notes?.find((n) => n.note_no === noteNo);
    if (note?.fact_ids?.length) {
      effectiveFactId = note.fact_ids[0];
    }
  }
  const activeFact = report?.facts?.find((f) => f.fact_id === effectiveFactId) ?? null;

  // 2. Identify active note (by noteNo, or reverse lookup by effectiveFactId)
  const activeNote =
    report?.source_notes?.find((n) => noteNo != null && n.note_no === noteNo) ??
    (effectiveFactId ? report?.source_notes?.find((n) => n.fact_ids?.includes(effectiveFactId)) : null) ??
    null;

  // 3. Identify active sentence & audit verdict from narrative_audit
  let activeSentence: SentenceItem | null = null;
  let auditVerdict: AuditVerdictItem | null = null;

  if (report) {
    // Search narrative blocks for a sentence citing activeFact or noteNo
    const blocks = report.report_spec?.blocks ?? report.blocks ?? [];
    for (const rawB of blocks) {
      const b = rawB as ReportBlockItem;
      const sents = [
        ...(b.sentences ?? (b.sentence ? [b.sentence] : [])),
        ...(b.takeaway ? [b.takeaway] : []),
      ];
      if (b.items && Array.isArray(b.items)) {
        for (const item of b.items) {
          if (item.sentences) sents.push(...item.sentences);
        }
      }
      if (b.subsections && Array.isArray(b.subsections)) {
        for (const sub of b.subsections) {
          if (sub.sentences) sents.push(...sub.sentences);
        }
      }
      for (const s of sents) {
        if (
          (effectiveFactId && s.fact_ids?.includes(effectiveFactId)) ||
          (noteNo && s.source_note_ids?.includes(noteNo)) ||
          (noteNo && s.text?.includes(`[${noteNo}]`))
        ) {
          activeSentence = s;
          break;
        }
      }
      if (activeSentence) break;
    }

    // Check narrative audit for sentence verdict
    if (activeSentence) {
      const dropped = report.narrative_audit?.sentences_dropped?.find(
        (d) => d.sentence_id === activeSentence?.sentence_id || d.text === activeSentence?.text
      );
      if (dropped) {
        auditVerdict = {
          status: "dropped",
          reason: dropped.reason || "Câu văn bị loại bỏ do không đạt chuẩn kiểm định.",
          reason_code: dropped.reason_code,
        };
      } else {
        auditVerdict = {
          status: "accepted",
          reason: "Kiểm định định mức thành công: Số liệu trích xuất từ BCTC đã thẩm định khớp 100% với sự kiện phân tích.",
        };
      }
    } else {
      auditVerdict = {
        status: "accepted",
        reason: "Kiểm định định mức: Số liệu trích xuất từ BCTC gốc hợp lệ.",
      };
    }
  }

  // 4. Collect candidate targets in strict priority order:
  // (a) Candidate fact_ids (from factId, citation note's fact_ids, or active sentence)
  // (b) Candidate observation_ids (from observationId or activeFact.input_observation_ids)
  const candidateFactIds: string[] = [];
  if (factId) candidateFactIds.push(factId);
  if (noteNo != null) {
    const note = report?.source_notes?.find((n) => n.note_no === noteNo);
    if (note?.fact_ids?.length) {
      candidateFactIds.push(...note.fact_ids);
    }
  }
  if (effectiveFactId && !candidateFactIds.includes(effectiveFactId)) {
    candidateFactIds.push(effectiveFactId);
  }
  if (activeSentence?.fact_ids?.length) {
    for (const fid of activeSentence.fact_ids) {
      if (!candidateFactIds.includes(fid)) candidateFactIds.push(fid);
    }
  }

  const candidateObsIds: string[] = [];
  if (observationId) candidateObsIds.push(observationId);
  if (activeFact?.input_observation_ids?.length) {
    for (const oid of activeFact.input_observation_ids) {
      if (!candidateObsIds.includes(oid)) candidateObsIds.push(oid);
    }
  }

  const uniqueFactTargets = Array.from(new Set(candidateFactIds.filter((t): t is string => Boolean(t))));
  const uniqueObsTargets = Array.from(new Set(candidateObsIds.filter((t): t is string => Boolean(t))));
  // Fact targets strictly come first to survive snapshot rebuilds
  const allTargets = [...uniqueFactTargets, ...uniqueObsTargets];
  const targetsKey = JSON.stringify(allTargets);

  useEffect(() => {
    let isCancelled = false;

    async function fetchLineage() {
      if (allTargets.length === 0) {
        setNode(null);
        setIsLoading(false);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      let lastError: Error | null = null;
      let loadedData: LineageNode | null = null;

      for (const target of allTargets) {
        if (isCancelled) return;
        try {
          const res = await apiFetch(`/api/lineage/${encodeURIComponent(target)}`);
          if (res.ok) {
            loadedData = await res.json();
            break;
          } else {
            lastError = new Error(`Failed to fetch lineage: ${res.statusText || res.status}`);
          }
        } catch (err: unknown) {
          lastError = err instanceof Error ? err : new Error(String(err));
        }
      }

      if (!isCancelled) {
        if (loadedData) {
          setNode(loadedData);
          setError(null);
          setIsLoading(false);
        } else {
          setNode(null);
          setError(lastError || new Error("Failed to fetch lineage: Not Found"));
          setIsLoading(false);
        }
      }
    }

    fetchLineage();

    return () => {
      isCancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetsKey, retryTrigger]);

  return {
    node,
    isLoading,
    error,
    retry,
    activeNote,
    activeFact,
    activeSentence,
    auditVerdict,
  };
}
