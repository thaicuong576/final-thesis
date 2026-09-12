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

  it('REGRESSION: does not pollute Macro-only scope with company metrics (NPL, Coverage, ROA, ROE)', () => {
    const question = 'Diễn biến chính sách tiền tệ và lãi suất điều hành trong năm 2024';
    const result = parseAnalysisQuestion(question, mockCapabilities);

    expect(result.mismatch.isMismatch).toBe(false);
    expect(result.scope.entities).toHaveLength(0);

    const capIds = result.scope.analysisPlan.selectedCapabilities.map((c) => c.id);
    expect(capIds).toEqual(['macro']);
    expect(capIds).not.toContain('company');
    expect(capIds).not.toContain('peer');

    // Crucial: company metrics must NOT be attached to a Macro-only request
    expect(result.scope.metrics).toHaveLength(0);
    expect(result.scope.scopeSignature).toBe('Toàn hệ thống · Q1–Q4/2024');
    expect(result.scope.scopeSignature).not.toContain('NPL');
    expect(result.scope.scopeSignature).not.toContain('Coverage');
    expect(result.scope.scopeSignature).not.toContain('ROA');
    expect(result.scope.scopeSignature).not.toContain('ROE');
  });

  it('REGRESSION A: "ROE của TCB thay đổi thế nào?" -> adjusting period/metric does not introduce Peer', () => {
    const question = 'ROE của TCB thay đổi thế nào?';
    const parsed = parseAnalysisQuestion(question, mockCapabilities);

    expect(parsed.scope.analysisPlan.selectedCapabilities.map((c) => c.id)).toEqual(['company']);

    // User adjusts period/metric in ScopeAdjustmentDrawer
    const replanned = planAnalyticalCapabilities({
      entities: parsed.scope.entities,
      capabilities: mockCapabilities,
      rawQuestion: parsed.rawQuestion
    });

    const replannedCapIds = replanned.map((c) => c.id);
    expect(replannedCapIds).toEqual(['company']);
    expect(replannedCapIds).not.toContain('peer');
    expect(replannedCapIds).not.toContain('macro');
  });

  it('REGRESSION B: "TCB sinh lời tốt hơn hay kém nhóm so sánh?" -> adjusting period/metric preserves Peer because QUESTION requires it', () => {
    const question = 'TCB sinh lời tốt hơn hay kém nhóm so sánh?';
    const parsed = parseAnalysisQuestion(question, mockCapabilities);

    expect(parsed.scope.analysisPlan.selectedCapabilities.map((c) => c.id)).toEqual(['company', 'peer']);

    // User adjusts period/metric in ScopeAdjustmentDrawer
    const replanned = planAnalyticalCapabilities({
      entities: parsed.scope.entities,
      capabilities: mockCapabilities,
      rawQuestion: parsed.rawQuestion
    });

    const replannedCapIds = replanned.map((c) => c.id);
    expect(replannedCapIds).toContain('company');
    expect(replannedCapIds).toContain('peer');
    expect(replannedCapIds).not.toContain('macro');
  });

  it('REGRESSION C: "Lãi suất điều hành liên quan thế nào đến TCB?" -> adjusting period still preserves Company + Macro', () => {
    const question = 'Lãi suất điều hành liên quan thế nào đến TCB?';
    const parsed = parseAnalysisQuestion(question, mockCapabilities);

    expect(parsed.scope.analysisPlan.selectedCapabilities.map((c) => c.id)).toEqual(['company', 'macro']);

    // User adjusts period only in ScopeAdjustmentDrawer
    const replanned = planAnalyticalCapabilities({
      entities: parsed.scope.entities,
      capabilities: mockCapabilities,
      rawQuestion: parsed.rawQuestion
    });

    const replannedCapIds = replanned.map((c) => c.id);
    expect(replannedCapIds).toContain('company');
    expect(replannedCapIds).toContain('macro');
    expect(replannedCapIds).not.toContain('peer');
  });

  it('resolves explicit supported years and quarters dynamically from a multi-year capability fixture', () => {
    const multiYearCapabilities = {
      ...mockCapabilities,
      periods: [
        { id: '2023-q1', quarter: 1, year: 2023 },
        { id: '2023-q2', quarter: 2, year: 2023 },
        { id: '2023-q3', quarter: 3, year: 2023 },
        { id: '2023-q4', quarter: 4, year: 2023 },
        { id: '2024-q1', quarter: 1, year: 2024 },
        { id: '2024-q2', quarter: 2, year: 2024 },
        { id: '2024-q3', quarter: 3, year: 2024 },
        { id: '2024-q4', quarter: 4, year: 2024 },
        { id: '2025-q1', quarter: 1, year: 2025 },
        { id: '2025-q2', quarter: 2, year: 2025 },
        { id: '2025-q3', quarter: 3, year: 2025 },
        { id: '2025-q4', quarter: 4, year: 2025 }
      ]
    };

    // 1. Explicit year only -> only that year's 4 quarters
    const resYearOnly = parseAnalysisQuestion('ROE của TCB trong năm 2024', multiYearCapabilities);
    expect(resYearOnly.mismatch.isMismatch).toBe(false);
    expect(resYearOnly.scope.periods).toHaveLength(4);
    expect(resYearOnly.scope.periods.every((p) => p.year === 2024)).toBe(true);
    expect(resYearOnly.scope.scopeSignature).toContain('Q1–Q4/2024');

    // 2. Both explicit year and quarter -> only Q4/2024
    const resYearAndQuarter = parseAnalysisQuestion('ROE TCB Q4/2024', multiYearCapabilities);
    expect(resYearAndQuarter.mismatch.isMismatch).toBe(false);
    expect(resYearAndQuarter.scope.periods).toHaveLength(1);
    expect(resYearAndQuarter.scope.periods[0]).toEqual({
      id: '2024-q4',
      quarter: 4,
      year: 2024
    });
    expect(resYearAndQuarter.scope.scopeSignature).toContain('Q4/2024');

    // 3. Neither explicit year nor quarter -> all 12 periods
    const resNoPeriod = parseAnalysisQuestion('ROE của TCB', multiYearCapabilities);
    expect(resNoPeriod.scope.periods).toHaveLength(12);
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
  });
});
