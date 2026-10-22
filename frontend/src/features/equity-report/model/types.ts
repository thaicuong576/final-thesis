export type QuestionType =
  | 'lookup'
  | 'company_profile'
  | 'ranking'
  | 'trend'
  | 'head_to_head'
  | 'sector_theme'
  | 'relationship';

export interface MetricPresentation {
  id: string;
  acronym: string;
  label: string;
  shortLabel: string;
  unit: string;
  direction: 'higher_is_better' | 'lower_is_better' | 'neutral';
  decimals: number;
  group: string;
  groupLabel: string;
}

export interface QuestionTypeInfo {
  id: QuestionType;
  label: string;
  example: string;
}

export interface Capabilities {
  snapshotId?: string | null;
  datasetId?: string | null;
  datasetSnapshotId?: string | null;
  dataset_snapshot_id?: string | null;
  analysis_available?: boolean;
  implemented_capabilities?: string[];
  database_status?: string;
  entities?: Record<string, unknown>[];
  periods?: Record<string, unknown>[];
  metrics?: MetricPresentation[];
  coverage?: { entity_id: string; period_id: string; metrics: string[] }[];
  topics?: Record<string, unknown>[];
  peerUniverse?: Record<string, unknown> | null;
  macro?: Record<string, unknown> | null;
  suggestedQuestions?: string[];
  questionTypes?: QuestionTypeInfo[];
  readiness?: string | null;
}

export type FactType =
  | 'value'
  | 'peer_median'
  | 'peer_rank'
  | 'gap_to_median'
  | 'delta'
  | 'median_delta'
  | 'pairwise_gap'
  | 'spread'
  | 'ratio_to_median'
  | 'derived_ratio'
  | 'lead_count'
  | 'outlier';

export interface Fact {
  fact_id: string;
  fact_type: FactType;
  entity_id: string | null;
  other_entity_id: string | null;
  universe_id: string | null;
  metric_id: string;
  period: string;
  from_period: string | null;
  value: number | null;
  unit: string;
  rank_better: number | null;
  rank_desc: number | null;
  denominator: number | null;
  formula_version: string;
  input_observation_ids: string[];
  input_fact_ids: string[];
}

export interface ProducedBy {
  tool: string;
  agent: string;
}

export interface DatasetRow {
  entity_id: string;
  metric_id: string;
  period: string;
  status: 'valid' | 'missing';
  value: number | null;
  observation_id: string | null;
  rank_better: number | null;
  rank_desc: number | null;
  missing_reason: string | null;
}

export interface ReferenceLine {
  kind: string;
  metric_id: string;
  period: string;
  value: number;
  fact_id: string | null;
}

export type DatasetShape =
  | 'kpi'
  | 'ranked_list'
  | 'series'
  | 'series_multi'
  | 'peer_table'
  | 'comparison_table'
  | 'paired';

export interface Dataset {
  dataset_id: string;
  shape: DatasetShape;
  title: string;
  produced_by: ProducedBy;
  metric_ids: string[];
  periods: string[];
  highlight_entity_ids: string[];
  rows: DatasetRow[];
  reference_lines: ReferenceLine[];
  allowed_charts: string[];
}

export type SentenceAuthor =
  | 'orchestrator'
  | 'company'
  | 'sector'
  | 'macro'
  | 'critic'
  | 'system';

export type SentenceSource = 'model' | 'deterministic_fallback';

export interface Sentence {
  sentence_id: string;
  text: string;
  fact_ids: string[];
  author: SentenceAuthor;
  source: SentenceSource;
  revision: number;
}

export type ChartType =
  | 'kpi_strip'
  | 'ranked_bar'
  | 'line_trend'
  | 'small_multiples'
  | 'scatter'
  | 'rank_heatmap'
  | 'grouped_bar'
  | 'comparison_table';

export interface AnswerBlock {
  type: 'answer';
  value_fact_id: string;
  sentences: Sentence[];
}

export interface HeadlineBlock {
  type: 'headline';
  sentence: Sentence;
}

export interface KeyPointItem {
  title: string;
  sentences: Sentence[];
}

export interface KeyPointsBlock {
  type: 'key_points';
  items: KeyPointItem[];
}

export interface SectionBlock {
  type: 'section';
  title: string;
  sentences: Sentence[];
}

export interface FigureBlock {
  type: 'figure';
  figure_no: number;
  chart: ChartType;
  dataset_id: string;
  title: string;
  takeaway: Sentence;
}

export interface CalloutBlock {
  type: 'callout';
  tone: 'notice' | 'warning';
  title: string;
  finding_id: string | null;
  sentences: Sentence[];
}

export interface TableBlock {
  type: 'table';
  dataset_id: string;
  title: string;
}

export type ReportBlock =
  | AnswerBlock
  | HeadlineBlock
  | KeyPointsBlock
  | SectionBlock
  | FigureBlock
  | CalloutBlock
  | TableBlock;

export interface ReportSpec {
  kind: 'answer_card' | 'note';
  note_label: string | null;
  blocks: ReportBlock[];
}

export type SignalVerdict =
  | 'above_peers'
  | 'in_line'
  | 'below_peers'
  | 'mixed'
  | 'insufficient_data';

export interface Signal {
  group: string;
  label: string;
  verdict: SignalVerdict;
  metric_ids: string[];
  fact_ids: string[];
}

export interface CrossLevelFinding {
  finding_id: string;
  kind: 'divergent_signals' | 'counter_trend' | 'cross_metric_extreme';
  severity: 'notice' | 'warning';
  text: string;
  fact_ids: string[];
  status: 'confirmed' | 'dismissed';
}

export type SentenceDropReason =
  | 'missing_fact_citation'
  | 'unknown_fact'
  | 'number_mismatch'
  | 'unit_mismatch'
  | 'rank_mismatch'
  | 'count_mismatch'
  | 'period_not_cited'
  | 'entity_not_in_plan'
  | 'trend_without_delta'
  | 'trend_direction_mismatch'
  | 'comparison_direction_mismatch'
  | 'metric_label_mismatch'
  | 'self_comparison'
  | 'causal_language'
  | 'investment_advice'
  | 'unresolved_critique';

export interface SentenceDropped {
  sentence_id: string;
  author: string;
  text: string;
  reason_code: SentenceDropReason;
  reason: string;
}

export interface BlockDropped {
  type: string;
  reason: string;
}

export interface NarrativeAudit {
  sentences_checked: number;
  sentences_accepted: number;
  sentences_dropped: SentenceDropped[];
  numbers_checked: number;
  numbers_matched: number;
  blocks_dropped: BlockDropped[];
  composition_source: 'model' | 'deterministic_fallback';
}

export interface SourceNote {
  note_no: number;
  source_id: string;
  title: string;
  url: string | null;
  locator: string | null;
  fact_ids: string[];
}

export interface ErrorInfo {
  code: string;
  message: string;
  suggestions: string[];
}

export interface AdaptiveReportResponse {
  report_id: string;
  status: string;
  report_version?: string | null;
  question_type?: QuestionType | null;
  report_spec?: ReportSpec | null;
  datasets?: Dataset[];
  facts?: Fact[];
  signals?: Signal[];
  cross_level_findings?: CrossLevelFinding[];
  narrative_audit?: NarrativeAudit | null;
  source_notes?: SourceNote[];
  error?: ErrorInfo | null;
  [key: string]: unknown;
}
