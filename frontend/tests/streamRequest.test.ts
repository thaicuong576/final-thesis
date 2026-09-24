import { describe, expect, it } from 'vitest';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';
import { parseAnalysisQuestion } from '../src/features/analysis-composer/model/intentParser';
import { buildSupportedStreamRequest } from '../src/features/create-analysis/model/streamRequest';
import type { AnalysisCapabilities } from '../src/entities/capability/model/types';

function readyCompanyCapabilities(overrides: Partial<AnalysisCapabilities> = {}): AnalysisCapabilities {
  return {
    ...mockCapabilities,
    analysis_available: true,
    dataset_snapshot_id: 'provider-snapshot-1',
    implemented_capabilities: ['company'],
    database_status: 'connected',
    ...overrides
  };
}

describe('buildSupportedStreamRequest', () => {
  it('sends the target and period named in a supported company question', () => {
    const capabilities = readyCompanyCapabilities();
    const question = 'Phân tích ROE của TCB trong năm 2024.';
    const scope = parseAnalysisQuestion(question, capabilities).scope;

    expect(buildSupportedStreamRequest(question, scope, capabilities)).toEqual({
      request: { query: question, target_ticker: 'TCB', peer_tickers: [], period: '2024' },
      reason: null
    });
  });

  it('blocks execution when the provider snapshot is not runnable', () => {
    const capabilities = readyCompanyCapabilities({
      analysis_available: false,
      dataset_snapshot_id: null,
      implemented_capabilities: [],
      database_status: 'disconnected'
    });
    const question = 'Phân tích ROE của ACB trong năm 2024.';
    const scope = parseAnalysisQuestion(question, capabilities).scope;

    expect(buildSupportedStreamRequest(question, scope, capabilities)).toMatchObject({
      request: null,
      reason: expect.stringContaining('snapshot dữ liệu đã kiểm định')
    });
  });

  it('blocks peer analysis when the API only implements company analysis', () => {
    const capabilities = readyCompanyCapabilities();
    const question = 'So sánh ROE của ACB và TCB trong năm 2024.';
    const scope = parseAnalysisQuestion(question, capabilities).scope;

    expect(buildSupportedStreamRequest(question, scope, capabilities)).toMatchObject({
      request: null,
      reason: expect.stringContaining('sector')
    });
  });

  it('blocks partial-year selections the API does not accept', () => {
    const capabilities = readyCompanyCapabilities();
    const question = 'Phân tích ROE của ACB tại Q1 và Q2/2024.';
    const scope = parseAnalysisQuestion(question, capabilities).scope;

    expect(scope.periods).toHaveLength(2);
    expect(buildSupportedStreamRequest(question, scope, capabilities)).toMatchObject({
      request: null,
      reason: expect.stringContaining('một quý hoặc một năm đầy đủ')
    });
  });

  it('blocks a period inferred from the preview when the question has no year or quarter', () => {
    const capabilities = readyCompanyCapabilities();
    const question = 'Phân tích ROE của TCB.';
    const scope = parseAnalysisQuestion(question, capabilities).scope;

    expect(buildSupportedStreamRequest(question, scope, capabilities)).toMatchObject({
      request: null,
      reason: expect.stringContaining('Câu hỏi cần nêu rõ năm hoặc quý')
    });
  });

  it('blocks metrics inferred from the preview when the question names no supported metric', () => {
    const capabilities = readyCompanyCapabilities();
    const question = 'Phân tích chỉ tiêu của TCB trong năm 2024.';
    const scope = parseAnalysisQuestion(question, capabilities).scope;

    expect(buildSupportedStreamRequest(question, scope, capabilities)).toMatchObject({
      request: null,
      reason: expect.stringContaining('Câu hỏi cần nêu rõ chỉ tiêu được hỗ trợ')
    });
  });
});
