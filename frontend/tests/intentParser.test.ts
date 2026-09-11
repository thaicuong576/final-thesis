import { describe, expect, it } from 'vitest';
import {
  parseAnalysisQuestion,
  formatPeriodsSignature,
  planAnalyticalCapabilities
} from '../src/features/analysis-composer/model/intentParser';
import { mockCapabilities } from '../src/entities/capability/api/mockCapabilityProvider';

describe('intentParser (Query-Adaptive & Capability-Driven)', () => {
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
    expect(capIds).toEqual(['company', 'peer']);
    expect(capIds).not.toContain('macro');
  });

  it('correctly produces Macro + Company capabilities when macroeconomic factors are mentioned', () => {
    const question = 'Lãi suất điều hành liên quan thế nào đến TCB?';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(false);
    expect(result.scope.entities.map((e) => e.ticker)).toContain('TCB');

    const capIds = result.scope.analysisPlan.selectedCapabilities.map((c) => c.id);
    expect(capIds).toEqual(['company', 'macro']);
    expect(capIds).not.toContain('peer');
  });

  it('correctly produces Peer/Sector-only capability when question asks for sector comparison without specific company', () => {
    const question = 'So sánh các chỉ tiêu nợ xấu toàn ngành ngân hàng';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(false);
    expect(result.scope.entities).toHaveLength(0);

    const capIds = result.scope.analysisPlan.selectedCapabilities.map((c) => c.id);
    expect(capIds).toEqual(['peer']);
    expect(capIds).not.toContain('company');
    expect(capIds).not.toContain('macro');
  });

  it('correctly produces Macro-only capability when question asks for macroeconomic policy without company or peer comparison', () => {
    const question = 'Diễn biến chính sách tiền tệ và lãi suất điều hành trong năm 2024';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(false);
    expect(result.scope.entities).toHaveLength(0);

    const capIds = result.scope.analysisPlan.selectedCapabilities.map((c) => c.id);
    expect(capIds).toEqual(['macro']);
    expect(capIds).not.toContain('company');
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

  it('REGRESSION: "ROE VIB 2025" must trigger mismatch on VIB and 2025 and NOT silently default to supported scope', () => {
    const question = 'ROE VIB 2025';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(true);
    expect(result.mismatch.unsupportedEntities).toContain('VIB');
    expect(result.mismatch.unsupportedPeriods).toContain('2025');
    expect(result.scope.entities).toHaveLength(0);
    expect(result.scope.periods).toHaveLength(0);
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

  it('formats periods dynamically without hardcoding 2024 or length === 4', () => {
    expect(formatPeriodsSignature([])).toBe('');
    expect(
      formatPeriodsSignature([
        { id: '1', year: 2024, quarter: 1 },
        { id: '2', year: 2024, quarter: 2 },
        { id: '3', year: 2024, quarter: 3 },
        { id: '4', year: 2024, quarter: 4 }
      ])
    ).toBe('Q1–Q4/2024');

    expect(
      formatPeriodsSignature([
        { id: '1', year: 2023, quarter: 1 },
        { id: '2', year: 2023, quarter: 2 }
      ])
    ).toBe('Q1–Q2/2023');

    expect(
      formatPeriodsSignature([
        { id: '1', year: 2025, quarter: 3 }
      ])
    ).toBe('Q3/2025');
  });

  it('planAnalyticalCapabilities automatically plans capabilities without manual specialist toggling', () => {
    const tcb = mockCapabilities.entities.find((e) => e.ticker === 'TCB')!;
    const acb = mockCapabilities.entities.find((e) => e.ticker === 'ACB')!;

    // Single entity without peer/macro cues -> company only
    const singlePlan = planAnalyticalCapabilities({
      entities: [tcb],
      capabilities: mockCapabilities
    });
    expect(singlePlan.map((c) => c.id)).toEqual(['company']);

    // Multiple entities -> company + peer automatically
    const multiPlan = planAnalyticalCapabilities({
      entities: [tcb, acb],
      capabilities: mockCapabilities
    });
    expect(multiPlan.map((c) => c.id)).toEqual(['company', 'peer']);

    // Single entity with forcePeerComparison -> company + peer
    const forcedPeerPlan = planAnalyticalCapabilities({
      entities: [tcb],
      capabilities: mockCapabilities,
      forcePeerComparison: true
    });
    expect(forcedPeerPlan.map((c) => c.id)).toEqual(['company', 'peer']);
  });
});
