import { describe, expect, it } from 'vitest';
import { parseAnalysisQuestion } from '../src/features/analysis-composer/model/intentParser';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';

describe('intentParser (Query-Adaptive)', () => {
  it('correctly produces Company-only capability for specific single-entity question', () => {
    const question = 'ROE của TCB thay đổi thế nào trong năm 2024?';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(false);
    expect(result.scope.entities.map((e) => e.ticker)).toEqual(['TCB']);
    expect(result.scope.metrics.map((m) => m.acronym)).toContain('ROE');
    expect(result.scope.scopeSignature).toContain('TCB');
    expect(result.scope.scopeSignature).toContain('ROE');

    const capIds = result.scope.analysisPlan.selectedCapabilities.map((c) => c.id);
    expect(capIds).toEqual(['company']);
    expect(capIds).not.toContain('peer');
    expect(capIds).not.toContain('macro');
  });

  it('correctly produces Company + Peer capabilities for comparative question', () => {
    const question = 'TCB sinh lời tốt hơn hay kém nhóm so sánh?';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(false);
    expect(result.scope.entities.map((e) => e.ticker)).toContain('TCB');

    const capIds = result.scope.analysisPlan.selectedCapabilities.map((c) => c.id);
    expect(capIds).toContain('company');
    expect(capIds).toContain('peer');
    expect(capIds).not.toContain('macro');
  });

  it('correctly produces Macro + Company capabilities when macroeconomic factors are mentioned', () => {
    const question = 'Lãi suất điều hành liên quan thế nào đến TCB?';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(false);
    expect(result.scope.entities.map((e) => e.ticker)).toContain('TCB');

    const capIds = result.scope.analysisPlan.selectedCapabilities.map((c) => c.id);
    expect(capIds).toContain('company');
    expect(capIds).toContain('macro');
    expect(capIds).not.toContain('peer');
  });

  it('correctly produces all three capabilities for broad contextual multi-bank request', () => {
    const question = 'So sánh chất lượng tài sản của ACB, TCB và MBB trong năm 2024 và tác động của môi trường vĩ mô.';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(false);
    expect(result.scope.entities.map((e) => e.ticker)).toEqual(['ACB', 'TCB', 'MBB']);
    expect(result.scope.periods).toHaveLength(4);
    expect(result.scope.topicLabels).toContain('Chất lượng tài sản');
    expect(result.scope.metrics.map((m) => m.acronym)).toEqual(expect.arrayContaining(['NPL', 'Coverage']));

    const capIds = result.scope.analysisPlan.selectedCapabilities.map((c) => c.id);
    expect(capIds).toContain('company');
    expect(capIds).toContain('peer');
    expect(capIds).toContain('macro');
  });

  it('detects scope mismatch when question asks for unsupported metrics (EPS, P/E) or past years (2023)', () => {
    const question = 'So sánh chỉ số EPS và P/E của ACB và VCB trong năm 2023.';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(true);
    expect(result.mismatch.unsupportedMetrics).toEqual(expect.arrayContaining(['EPS', 'P/E']));
    expect(result.mismatch.unsupportedPeriods).toEqual(['2023']);
    expect(result.mismatch.reason).toContain('không có');
  });

  it('detects scope mismatch when question asks for banks not in the validated dataset', () => {
    const question = 'Đánh giá nợ xấu của BIDV và CTG trong năm 2024.';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(true);
    expect(result.mismatch.unsupportedEntities).toEqual(expect.arrayContaining(['BIDV', 'CTG']));
  });

  it('defaults to all entities and periods when question is high-level', () => {
    const question = 'Đánh giá khả năng sinh lời toàn ngành ngân hàng.';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(false);
    expect(result.scope.entities).toHaveLength(5);
    expect(result.scope.periods).toHaveLength(4);
    expect(result.scope.metrics.map((m) => m.acronym)).toEqual(expect.arrayContaining(['ROA', 'ROE']));
    expect(result.scope.analysisPlan.selectedCapabilities.map((c) => c.id)).toContain('peer');
  });
});
