import { describe, expect, it } from 'vitest';
import { normalizeLimitations } from '../src/features/onboarding/normalizeLimitations';

describe('normalizeLimitations', () => {
  it('returns a single-element array when given a non-empty string', () => {
    const input = 'Số liệu VIB do người dùng cung cấp; chưa được duyệt độc lập.';
    expect(normalizeLimitations(input)).toEqual([input]);
  });

  it('trims leading/trailing whitespace from string', () => {
    expect(normalizeLimitations('  Giới hạn sử dụng  ')).toEqual(['Giới hạn sử dụng']);
  });

  it('returns an empty array when given an empty or whitespace string', () => {
    expect(normalizeLimitations('')).toEqual([]);
    expect(normalizeLimitations('   \n\t  ')).toEqual([]);
  });

  it('returns an array of trimmed non-empty strings when given a string array', () => {
    const input = [' Dòng 1 ', '', 'Dòng 2', '   '];
    expect(normalizeLimitations(input)).toEqual(['Dòng 1', 'Dòng 2']);
  });

  it('returns an empty array when given an empty array', () => {
    expect(normalizeLimitations([])).toEqual([]);
  });

  it('returns an empty array when given null or undefined', () => {
    expect(normalizeLimitations(null)).toEqual([]);
    expect(normalizeLimitations(undefined)).toEqual([]);
  });

  it('returns an empty array when given non-string non-array types', () => {
    expect(normalizeLimitations(123)).toEqual([]);
    expect(normalizeLimitations({})).toEqual([]);
    expect(normalizeLimitations(true)).toEqual([]);
  });
});
