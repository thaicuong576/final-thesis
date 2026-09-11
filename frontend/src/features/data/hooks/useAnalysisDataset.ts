import { useQuery } from '@tanstack/react-query';
import { datasetService } from '../../../entities/dataset/api/datasetService';

export function useAnalysisDataset() {
  return useQuery({
    queryKey: ['active-analysis-dataset'],
    queryFn: datasetService.getActiveDataset
  });
}
