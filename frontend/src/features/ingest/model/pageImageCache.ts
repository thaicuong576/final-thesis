// In-memory cache by `${filingId}:${pageNumber}` so reopening a page is instant
export const pageImageCache = new Map<string, Blob>();

export function clearPageImageCache(): void {
  pageImageCache.clear();
}
