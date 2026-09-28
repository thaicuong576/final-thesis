import { useContext } from 'react';
import { useQuery, QueryClient, QueryClientContext } from '@tanstack/react-query';
import { capabilityService } from '../../../entities/capability/api/capabilityService';

let fallbackClient: QueryClient | undefined;
function getFallbackClient() {
  if (!fallbackClient) {
    fallbackClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } }
    });
  }
  return fallbackClient;
}

export function useAnalysisCapabilities() {
  const contextClient = useContext(QueryClientContext);
  const client = contextClient ?? getFallbackClient();

  return useQuery(
    {
      queryKey: ['analysis-capabilities'],
      queryFn: capabilityService.getCapabilities
    },
    client
  );
}
