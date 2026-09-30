import type { Dataset, FigureBlock, ReportBlock, ReportSpec, Sentence } from './types';

type ReportKind = ReportSpec['kind'];

/** A figure after normalization may carry takeaways merged from duplicate figures. */
export type NormalizedFigureBlock = FigureBlock & { extra_takeaways?: Sentence[] };
export type NormalizedBlock = Exclude<ReportBlock, FigureBlock> | NormalizedFigureBlock;

/**
 * Presentation-only cleanup of a composed report spec.
 *
 * The composer can repeat the same chart over the same dataset (one figure per metric) or,
 * in an answer card, add a KPI strip that repeats the answer number. Neither adds information,
 * so duplicates are folded into the first figure (their takeaway sentences are kept) and
 * figures are renumbered. Sentences and facts are never altered.
 */
export function normalizeBlocks(
  blocks: ReportBlock[],
  kind: ReportKind | undefined,
  datasets: Dataset[] = []
): NormalizedBlock[] {
  const out: NormalizedBlock[] = [];
  const firstFigure = new Map<string, NormalizedFigureBlock>();
  const hasAnswer = blocks.some((b) => b.type === 'answer');

  for (const block of blocks) {
    if (block.type !== 'figure') {
      out.push(block);
      continue;
    }
    if (kind === 'answer_card' && hasAnswer && block.chart === 'kpi_strip') {
      continue;
    }
    const dataset = datasets.find((d) => d.dataset_id === block.dataset_id);
    // Bars of metrics with different scales (coverage ~100%, NPL ~1%) on one axis flatten the small
    // ones into slivers; a comparison table reads correctly for any mix of metrics.
    const chart =
      block.chart === 'grouped_bar' && (dataset?.metric_ids?.length ?? 0) > 1 ? 'comparison_table' : block.chart;
    const key = `${chart}::${block.dataset_id}`;
    const existing = firstFigure.get(key);
    if (existing) {
      if (block.takeaway) {
        existing.extra_takeaways = [...(existing.extra_takeaways || []), block.takeaway];
      }
      // The first figure's title named one metric; the merged figure shows the whole dataset.
      if (dataset?.title) existing.title = dataset.title;
      continue;
    }
    const copy: NormalizedFigureBlock = { ...block, chart };
    firstFigure.set(key, copy);
    out.push(copy);
  }

  let n = 0;
  for (const block of out) {
    if (block.type === 'figure') {
      n += 1;
      block.figure_no = n;
    }
  }
  return out;
}
