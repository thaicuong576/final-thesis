/**
 * React hooks for Market Context with HOSE hours & tab visibility aware polling.
 */

import { useContext } from "react";
import { useQuery, QueryClient, QueryClientContext } from "@tanstack/react-query";
import type { MarketQuotesResponse, MarketValuationResponse } from "./types";
import { getApiBaseUrl } from "../../shared/lib/apiUrl";
import { apiFetch } from "@/shared/api/apiClient";

/**
 * Check if HOSE market is open (Mon-Fri 09:00 - 15:00 UTC+7).
 */
export function isHoseMarketOpen(now: Date = new Date()): boolean {
  const utcHours = now.getUTCHours();
  const utcMinutes = now.getUTCMinutes();
  const totalVnMinutes = (utcHours + 7) * 60 + utcMinutes;
  const vnDay = (now.getUTCDay() + Math.floor((utcHours + 7) / 24)) % 7;

  // 0 is Sunday, 6 is Saturday
  if (vnDay === 0 || vnDay === 6) {
    return false;
  }
  const currentDayMins = totalVnMinutes % (24 * 60);
  // 09:00 (540 mins) to 15:00 (900 mins)
  return currentDayMins >= 540 && currentDayMins <= 900;
}

let fallbackClient: QueryClient | undefined;
function getFallbackClient(): QueryClient {
  if (!fallbackClient) {
    fallbackClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } }
    });
  }
  return fallbackClient;
}

export function useMarketQuotes() {
  const contextClient = useContext(QueryClientContext);
  const client = contextClient ?? getFallbackClient();

  return useQuery<MarketQuotesResponse>(
    {
      queryKey: ["market-quotes"],
      queryFn: async () => {
        const base = getApiBaseUrl();
        const res = await apiFetch(`${base}/api/market/quotes`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      },
      refetchInterval: () => (!document.hidden && isHoseMarketOpen() ? 30000 : false),
      refetchIntervalInBackground: false,
    },
    client
  );
}

export function useMarketValuation() {
  const contextClient = useContext(QueryClientContext);
  const client = contextClient ?? getFallbackClient();

  return useQuery<MarketValuationResponse>(
    {
      queryKey: ["market-valuation"],
      queryFn: async () => {
        const base = getApiBaseUrl();
        const res = await apiFetch(`${base}/api/market/valuation`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      },
      refetchInterval: () => (!document.hidden && isHoseMarketOpen() ? 30000 : false),
      refetchIntervalInBackground: false,
    },
    client
  );
}
