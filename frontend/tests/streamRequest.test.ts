import { describe, expect, it } from 'vitest';
import { buildSupportedStreamRequest } from '../src/features/create-analysis/model/streamRequest';

describe('buildSupportedStreamRequest (lean ER-6 contract)', () => {
  it('sends query directly without client-side blocking', () => {
    const question = 'Phân tích ROE của TCB trong năm 2024.';
    const result = buildSupportedStreamRequest(question);

    expect(result).toEqual({
      request: { query: question },
      reason: null
    });
  });

  it('permits questions with periods or metrics unknown to client', () => {
    const question = 'Tỷ lệ nợ xấu của ACB quý 4/2023';
    const result = buildSupportedStreamRequest(question);

    expect(result).toEqual({
      request: { query: question },
      reason: null
    });
  });

  it('rejects empty or whitespace-only questions with a friendly message', () => {
    expect(buildSupportedStreamRequest('')).toEqual({
      request: null,
      reason: 'Vui lòng nhập câu hỏi phân tích.'
    });
    expect(buildSupportedStreamRequest('   ')).toEqual({
      request: null,
      reason: 'Vui lòng nhập câu hỏi phân tích.'
    });
  });
});
