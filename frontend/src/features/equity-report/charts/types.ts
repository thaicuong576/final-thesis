import type { Dataset, MetricPresentation } from '../model/types';

export interface ChartProps {
  dataset: Dataset;
  metrics?: MetricPresentation[];
  highlight?: string[];
  className?: string;
}
