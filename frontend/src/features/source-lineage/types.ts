/**
 * Source Lineage and Drawer types (LIN-1).
 */

export interface LineageReceiptInput {
  observation_id: string;
  metric_id: string;
  value: string;
  unit: string;
  period_id: string;
  entity_id?: string;
  entity?: string;
  reporting_scope?: string;
  period_basis?: string;
}

export interface LineageCalculationReceipt {
  formula_version?: string;
  result?: string;
  tolerance?: string;
  calculated_output?: string;
  candidate_output?: string;
  absolute_difference?: string;
  unit?: string;
  ordered_inputs?: LineageReceiptInput[];
}

export interface LineageNode {
  observation_id: string;
  entity: string;
  entity_id?: string | null;
  metric: string;
  metric_id?: string | null;
  metric_name?: string | null;
  period: string;
  period_id?: string | null;
  value?: number | null;
  unit?: string | null;
  formula_version?: string | null;
  receipt_result?: string | null;
  receipt_tolerance?: string | null;
  calculation_receipt?: LineageCalculationReceipt | null;
  source_title?: string | null;
  source_url?: string | null;
  page?: number | null;
  section?: string | null;
  row_label?: string | null;
  reading?: string | null;
  children: LineageNode[];
}

export type LineageTab = "document" | "data" | "journey";

export interface JourneyStep {
  id: string;
  stepNumber: number;
  label: string;
  title: string;
  detail: string;
  meta?: string;
  tabTarget?: LineageTab;
  badge?: string;
  badgeType?: "success" | "neutral" | "warning";
}

export interface SourceNoteItem {
  note_no: number;
  source_id: string;
  title: string;
  url?: string | null;
  locator?: string | null;
  page?: number | null;
  fact_ids?: string[];
}

export interface FactItem {
  fact_id: string;
  fact_type: string;
  entity_id?: string | null;
  other_entity_id?: string | null;
  universe_id?: string | null;
  metric_id?: string | null;
  period?: string | null;
  from_period?: string | null;
  value?: number | null;
  unit?: string | null;
  rank_better?: number | null;
  rank_desc?: number | null;
  denominator?: number | null;
  formula_version?: string | null;
  input_observation_ids?: string[];
  input_fact_ids?: string[];
}

export interface SentenceItem {
  sentence_id?: string;
  text?: string;
  fact_ids?: string[];
  source_note_ids?: number[];
}

export interface AuditVerdictItem {
  status: "accepted" | "dropped";
  reason: string;
  reason_code?: string;
}

export interface ReportBlockItem {
  sentences?: SentenceItem[];
  sentence?: SentenceItem;
  items?: Array<{ sentences?: SentenceItem[] }>;
  subsections?: Array<{ sentences?: SentenceItem[] }>;
  takeaway?: SentenceItem;
  [key: string]: unknown;
}

export interface ReportItem {
  report_id?: string;
  question_type?: string | null;
  synthesis_summary?: string;
  source_notes?: SourceNoteItem[];
  facts?: FactItem[];
  narrative_audit?: {
    sentences_dropped?: Array<{
      sentence_id?: string;
      text?: string;
      reason?: string;
      reason_code?: string;
    }>;
  } | null;
  report_spec?: {
    blocks?: unknown[];
  } | null;
  blocks?: unknown[];
}

export interface SourceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  noteNo?: number;
  factId?: string;
  observationId?: string;
  report?: ReportItem | null;
  defaultTab?: LineageTab;
}
