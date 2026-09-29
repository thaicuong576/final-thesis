import { describe, expect, it } from 'vitest';

/**
 * Calculates WCAG 2.1 relative luminance for an sRGB color.
 * Standard formula: https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 */
export function hexToRgb(hex: string): [number, number, number] {
  const cleanHex = hex.replace(/^#/, '');
  const r = parseInt(cleanHex.substring(0, 2), 16);
  const g = parseInt(cleanHex.substring(2, 4), 16);
  const b = parseInt(cleanHex.substring(4, 6), 16);
  return [r, g, b];
}

export function channelToLinear(channel: number): number {
  const c = channel / 255;
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

export function getRelativeLuminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex);
  return 0.2126 * channelToLinear(r) + 0.7152 * channelToLinear(g) + 0.0722 * channelToLinear(b);
}

/**
 * Calculates WCAG 2.1 contrast ratio between two colors (1:1 to 21:1).
 * Standard formula: https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
 */
export function calculateContrastRatio(foregroundHex: string, backgroundHex: string): number {
  const l1 = getRelativeLuminance(foregroundHex);
  const l2 = getRelativeLuminance(backgroundHex);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe('Design System WCAG AA Color Contrast Verification', () => {
  // 3 Target surfaces specified by design guidelines & user review
  const BACKGROUNDS = {
    'surface-primary (#fbfbf8)': '#fbfbf8',
    'surface-secondary (#f2f2ec)': '#f2f2ec',
    'warning-soft (#fbefcf)': '#fbefcf'
  };

  // Text tokens mapped in tailwind.config.ts / index.css
  const TEXT_TOKENS = {
    '--text-primary (#20201e)': '#20201e',
    '--text-secondary / --text-muted (#62625d)': '#62625d',
    '--text-accent-strong (#8a5a00)': '#8a5a00',
    '--text-warning-strong (#8a5a00)': '#8a5a00',
    '--text-success-strong (#1b6d41)': '#1b6d41'
  };

  const WCAG_AA_MINIMUM = 4.5;

  Object.entries(TEXT_TOKENS).forEach(([tokenName, textColor]) => {
    Object.entries(BACKGROUNDS).forEach(([bgName, bgColor]) => {
      it(`${tokenName} meets WCAG AA (>= 4.5:1) on ${bgName}`, () => {
        const ratio = calculateContrastRatio(textColor, bgColor);
        expect(ratio).toBeGreaterThanOrEqual(WCAG_AA_MINIMUM);
      });
    });
  });

  describe('Verification that raw palette colors fail AA and must never be used as text', () => {
    it('--accent (#ee9f0d) fails WCAG AA on all 3 backgrounds (< 4.5:1)', () => {
      Object.values(BACKGROUNDS).forEach((bgColor) => {
        const ratio = calculateContrastRatio('#ee9f0d', bgColor);
        expect(ratio).toBeLessThan(WCAG_AA_MINIMUM);
        // Specifically ~1.9:1 to 2.1:1 as noted in review
        expect(ratio).toBeLessThan(2.5);
      });
    });

    it('--warning (#cf8500) fails WCAG AA on all 3 backgrounds (< 4.5:1)', () => {
      Object.values(BACKGROUNDS).forEach((bgColor) => {
        const ratio = calculateContrastRatio('#cf8500', bgColor);
        expect(ratio).toBeLessThan(WCAG_AA_MINIMUM);
        // Specifically ~2.6:1 to 2.9:1 as noted in review
        expect(ratio).toBeLessThan(3.0);
      });
    });
  });
});
