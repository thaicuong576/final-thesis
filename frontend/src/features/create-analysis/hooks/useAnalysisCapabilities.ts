import { useQuery } from '@tanstack/react-query';
import { capabilityService } from '../../../entities/capability/api/capabilityService';

export function useAnalysisCapabilities() {
  return useQuery({
    queryKey: ['analysis-capabilities'],
    queryFn: capabilityService.getCapabilities
  });
}
