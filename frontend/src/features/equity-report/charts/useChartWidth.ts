import { useState, useEffect, type RefObject } from 'react';

/**
 * Hook to measure container width via ResizeObserver.
 * Ensures SVG viewBox matches rendered pixel width 1:1, preventing font enlargement.
 * Defaults to 560px for headless/test environments.
 */
export function useChartWidth(ref: RefObject<HTMLElement | null>, defaultWidth = 560): number {
  const [width, setWidth] = useState<number>(defaultWidth);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const measure = () => {
      const clientW = el.clientWidth;
      if (clientW > 0) {
        setWidth(clientW);
      }
    };

    measure();

    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const w = entry.contentRect.width;
          if (w > 0) {
            setWidth(Math.round(w));
          }
        }
      });
      observer.observe(el);
      return () => observer.disconnect();
    }
  }, [ref, defaultWidth]);

  return width;
}
