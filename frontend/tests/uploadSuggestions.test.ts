import { describe, expect, it } from 'vitest';
import {
  buildUploadSuggestions,
  findFirstPeer,
  formatQuarterVi,
} from '../src/features/onboarding/uploadSuggestions';
import type { AnalysisCapabilities } from '../src/entities/capability/model/types';

const mockCapabilities: AnalysisCapabilities = {
  analysis_available: true,
  implemented_capabilities: ['company', 'sector'],
  dataset_snapshot_id: 'snapshot-2024q4',
  entities: [
    { id: 'ACB', ticker: 'ACB', name: 'Ngân hàng Á Châu' },
    { id: 'MBB', ticker: 'MBB', name: 'Ngân hàng Quân đội' },
    { id: 'TCB', ticker: 'TCB', name: 'Techcombank' },
    { id: 'VCB', ticker: 'VCB', name: 'Vietcombank' },
    { id: 'VPB', ticker: 'VPB', name: 'VPBank' },
  ],
  periods: [
    { id: '2024_Q1', quarter: 1, year: 2024 },
    { id: '2024_Q2', quarter: 2, year: 2024 },
    { id: '2024_Q3', quarter: 3, year: 2024 },
    { id: '2024_Q4', quarter: 4, year: 2024 },
  ],
  metrics: [],
  suggestedQuestions: [],
  topics: [],
  macro: {
    status: 'AVAILABLE',
    minimumContractSatisfied: true,
    summary: '',
    details: '',
  },
};

describe('uploadSuggestions', () => {
  describe('formatQuarterVi', () => {
    it('formats valid period IDs to Vietnamese quarter format', () => {
      expect(formatQuarterVi('2025_Q4')).toBe('quý 4/2025');
      expect(formatQuarterVi('2024_Q1')).toBe('quý 1/2024');
      expect(formatQuarterVi('2023-Q3')).toBe('quý 3/2023');
      expect(formatQuarterVi('2025Q2')).toBe('quý 2/2025');
    });

    it('returns null for missing or unparseable periods', () => {
      expect(formatQuarterVi(undefined)).toBeNull();
      expect(formatQuarterVi(null)).toBeNull();
      expect(formatQuarterVi('')).toBeNull();
      expect(formatQuarterVi('invalid_period')).toBeNull();
      expect(formatQuarterVi('2025')).toBeNull();
    });
  });

  describe('findFirstPeer', () => {
    it('returns the first bank not matching the given entity', () => {
      expect(findFirstPeer('VIB', mockCapabilities)).toBe('ACB');
      expect(findFirstPeer('vib', mockCapabilities)).toBe('ACB');
      expect(findFirstPeer('ACB', mockCapabilities)).toBe('MBB');
    });

    it('returns null when no capabilities or entities are available', () => {
      expect(findFirstPeer('VIB', null)).toBeNull();
      expect(findFirstPeer('VIB', { entities: [] })).toBeNull();
      expect(findFirstPeer('VIB', { entities: [{ id: 'VIB', ticker: 'VIB', name: 'VIB' }] })).toBeNull();
    });
  });

  describe('buildUploadSuggestions', () => {
    it('builds three suggestions for VIB and 2025_Q4 using the uploaded period', () => {
      const suggestions = buildUploadSuggestions('VIB', '2025_Q4', mockCapabilities);

      expect(suggestions).toEqual([
        'Tỷ lệ nợ xấu của VIB quý 4/2025 là bao nhiêu?',
        'Sức khỏe tài chính của VIB quý 4/2025 so với nhóm',
        'So sánh VIB và ACB quý 4/2025',
      ]);
      expect(suggestions.join(' ')).not.toContain('2024');
    });

    it('accepts parameter object syntax', () => {
      const suggestions = buildUploadSuggestions({
        entity: 'VIB',
        periodId: '2025_Q4',
        capabilities: mockCapabilities,
      });

      expect(suggestions).toEqual([
        'Tỷ lệ nợ xấu của VIB quý 4/2025 là bao nhiêu?',
        'Sức khỏe tài chính của VIB quý 4/2025 so với nhóm',
        'So sánh VIB và ACB quý 4/2025',
      ]);
    });

    it('selects the next available bank when the entity is the first bank in catalog', () => {
      const suggestions = buildUploadSuggestions('ACB', '2024_Q4', mockCapabilities);

      expect(suggestions[2]).toBe('So sánh ACB và MBB quý 4/2024');
    });

    it('omits third suggestion when no peer bank is available', () => {
      const suggestions = buildUploadSuggestions('VIB', '2025_Q4', null);

      expect(suggestions).toHaveLength(2);
      expect(suggestions).toEqual([
        'Tỷ lệ nợ xấu của VIB quý 4/2025 là bao nhiêu?',
        'Sức khỏe tài chính của VIB quý 4/2025 so với nhóm',
      ]);
    });

    it('formats suggestions without period when period is missing or cannot be parsed', () => {
      const missingPeriod = buildUploadSuggestions('VIB', undefined, mockCapabilities);
      expect(missingPeriod).toEqual([
        'Tỷ lệ nợ xấu của VIB là bao nhiêu?',
        'Sức khỏe tài chính của VIB so với nhóm',
        'So sánh VIB và ACB',
      ]);

      const invalidPeriod = buildUploadSuggestions('VIB', 'invalid', mockCapabilities);
      expect(invalidPeriod).toEqual([
        'Tỷ lệ nợ xấu của VIB là bao nhiêu?',
        'Sức khỏe tài chính của VIB so với nhóm',
        'So sánh VIB và ACB',
      ]);
    });

    it('returns empty array when entity is empty', () => {
      expect(buildUploadSuggestions('', '2025_Q4', mockCapabilities)).toEqual([]);
    });
  });
});
