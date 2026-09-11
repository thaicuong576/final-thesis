import { getMockAnalysisDataset } from './mockDatasetProvider';
import type { AnalysisDataset } from '../model/types';

export interface DatasetService {
  getActiveDataset(): Promise<AnalysisDataset>;
}

// Replace this implementation with the dataset API without changing the Data surface.
export const datasetService: DatasetService = {
  getActiveDataset: getMockAnalysisDataset
};
